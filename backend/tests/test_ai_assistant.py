from copy import deepcopy

from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Attribution, Evidence, Finding, RiskIndicator
from app.services.ai_provider import AIProvider, ProviderUnavailableError, UnavailableAIProvider
from app.services.ai_service import AIService, SYSTEM_PROMPT
from app.services.attribution_service import AttributionService
from app.services.demo_case_seeder import seed_demo_case
from app.services.evidence_service import EvidenceService
from app.services.risk_analysis_service import RiskAnalysisService

client = TestClient(app)


class FakeProvider(AIProvider):
    name = "fake-test-provider"

    def __init__(self):
        self.system_prompt = None
        self.context = None

    def generate(self, system_prompt, context, request):
        self.system_prompt = system_prompt
        self.context = deepcopy(context)
        return f"Grounded response for {request}."


def setup_demo_analysis():
    seed_demo_case()
    RiskAnalysisService().analyze_case("CASE-DEMO-001")
    AttributionService().attribute_case("CASE-DEMO-001")
    EvidenceService().collect_case("CASE-DEMO-001")


def counts():
    with SessionLocal() as session:
        return (
            session.query(RiskIndicator).count(),
            session.query(Finding).count(),
            session.query(Attribution).count(),
            session.query(Evidence).count(),
        )


def test_unconfigured_provider_is_explicitly_unavailable():
    try:
        UnavailableAIProvider().generate("system", {}, "request")
        assert False, "Expected provider unavailable error"
    except ProviderUnavailableError as exc:
        assert "no provider is configured" in str(exc)


def test_context_is_structured_and_provider_receives_only_context():
    setup_demo_analysis()
    provider = FakeProvider()
    result = AIService(provider=provider).summary("CASE-DEMO-001")

    assert result["ai_assisted"] is True
    assert result["provider"] == "fake-test-provider"
    assert provider.system_prompt == SYSTEM_PROMPT
    assert "transactions" in provider.context
    assert "api_key" not in str(provider.context).lower()
    assert result["evidence_refs"]


def test_ai_functions_do_not_change_deterministic_records():
    setup_demo_analysis()
    before = counts()
    service = AIService(provider=UnavailableAIProvider())
    for function in (service.summary, service.explain_path, service.explain_risk, service.explain_attribution, service.next_steps):
        result = function("CASE-DEMO-001")
        assert result["provider_status"] == "unavailable"
        assert result["ai_assisted"] is False
    assert counts() == before


def test_ai_endpoints_return_grounded_unavailable_responses():
    setup_demo_analysis()
    endpoints = [
        ("/cases/CASE-DEMO-001/ai/summary", None),
        ("/cases/CASE-DEMO-001/ai/explain-path", {"path_rank": 1}),
        ("/cases/CASE-DEMO-001/ai/explain-risk", None),
        ("/cases/CASE-DEMO-001/ai/explain-attribution", {"wallet": "0x1111111111111111111111111111111111111111"}),
        ("/cases/CASE-DEMO-001/ai/next-steps", None),
    ]
    for endpoint, payload in endpoints:
        response = client.post(endpoint, json=payload) if payload else client.post(endpoint)
        assert response.status_code == 200
        body = response.json()
        assert body["provider_status"] == "unavailable"
        assert body["ai_assisted"] is False
        assert "unavailable" in body["answer"].lower()
        assert "limitations" in body


def test_missing_case_is_rejected():
    response = client.post("/cases/NO-SUCH-CASE/ai/summary")
    assert response.status_code == 404
