from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Case, Evidence, Report, Transaction
from app.services.attribution_service import AttributionService
from app.services.demo_case_seeder import seed_demo_case
from app.services.evidence_service import EvidenceService
from app.services.risk_analysis_service import RiskAnalysisService
from app.services.transaction_graph_service import TransactionGraphService


class ReportService:
    VERSION = "1.0"

    def __init__(self, session_factory=SessionLocal, output_dir: Path | None = None) -> None:
        self.session_factory = session_factory
        self.output_dir = output_dir or Path(__file__).resolve().parents[2] / "reports"
        init_db()

    @staticmethod
    def _safe(text: Any) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _case_transactions(session: Session, case: Case) -> list[Transaction]:
        addresses = [wallet.address for wallet in case.wallets]
        if not addresses:
            return []
        return (
            session.query(Transaction)
            .filter((Transaction.from_address.in_(addresses)) | (Transaction.to_address.in_(addresses)))
            .order_by(Transaction.timestamp.asc(), Transaction.id.asc())
            .all()
        )

    def generate(self, case_id: str) -> tuple[Path, dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None and (settings.demo_mode or settings.environment.lower() == "demo"):
            seed_demo_case(self.session_factory)
            with self.session_factory() as session:
                case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None:
            raise ValueError("Case not found.")

        RiskAnalysisService(self.session_factory).analyze_case(case_id)
        AttributionService(self.session_factory).attribute_case(case_id)
        TransactionGraphService(self.session_factory).build_case_graph(case_id)
        EvidenceService(self.session_factory).collect_case(case_id)

        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            transactions = self._case_transactions(session, case)
            risk = RiskAnalysisService(self.session_factory).analyze_transactions(transactions)
            graph = TransactionGraphService.build_graph(transactions)
            paths = []
            for wallet in sorted({item.from_address for item in transactions}):
                paths.extend(TransactionGraphService.trace_paths_from_transactions(transactions, wallet))
            attributions = AttributionService.attribute_wallets(case.wallets, AttributionService.seed_demo_entities(session))
            evidence = session.query(Evidence).filter(Evidence.case_id == case.id).all()
            report_id = f"RPT-{hashlib.sha256(f'{case_id}|{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:16]}"
            generated_at = datetime.now(timezone.utc)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{report_id}.pdf"
            self._write_pdf(output_path, case, transactions, graph, paths, risk, attributions, evidence, report_id, generated_at)
            report = Report(report_id=report_id, case_id=case.id, generated_at=generated_at, version=self.VERSION, file_path=str(output_path))
            session.add(report)
            session.commit()
            metadata = {
                "report_id": report_id,
                "case_id": case.case_id,
                "generated_at": generated_at.isoformat(),
                "version": self.VERSION,
                "filename": output_path.name,
            }
            return output_path, metadata

    def _write_pdf(self, path, case, transactions, graph, paths, risk, attributions, evidence, report_id, generated_at):
        styles = getSampleStyleSheet()
        story = [Paragraph("ChainGuard Investigation Report", styles["Title"]), Paragraph("DEMO/SAMPLE - Investigative intelligence, not proof of ownership or criminality", styles["Normal"]), Spacer(1, 0.2 * inch)]

        def heading(text):
            story.extend([Spacer(1, 0.12 * inch), Paragraph(text, styles["Heading2"])])

        def table(rows):
            rendered = [[Paragraph(self._safe(cell), styles["BodyText"]) for cell in row] for row in rows]
            item = Table(rendered, repeatRows=1, hAlign="LEFT")
            item.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17343b")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ccd7d7")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f5")])]))
            story.append(item)

        heading("Case information")
        table([["Field", "Value"], ["Case ID", case.case_id], ["Complaint/reference", case.complaint_ref or "-"], ["Status", case.status], ["Blockchain", "Ethereum / DEMO"], ["Reported wallet", case.wallets[0].address if case.wallets else "-"], ["Created", case.created_at.isoformat()]])
        heading("Executive summary")
        table([["Measure", "Value"], ["Investigation scope", "Normalized synthetic transaction activity"], ["Transactions analyzed", str(len(transactions))], ["Wallets discovered", str(len(graph["nodes"]))], ["Hops analyzed", str(max((path["hop_count"] for path in paths), default=0))], ["Overall risk", f"{risk['overall_score']}/100 ({risk['risk_level']})"]])
        heading("Transaction findings")
        table([["Transaction", "From", "To", "Value", "Timestamp"], *[[tx.tx_hash, tx.from_address, tx.to_address, f"{tx.value} {tx.token or 'native'}", tx.timestamp.isoformat()] for tx in transactions]])
        heading("Fund-flow findings")
        table([["Rank", "Path", "Hops", "Total value"], *[[str(item["rank"]), " -> ".join(item["wallets"]), str(item["hop_count"]), item["total_value"]] for item in paths[:12]]])
        heading("Risk findings")
        table([["Indicator", "Severity", "Score", "Explanation"], *[[item["type"], item["severity"], str(item["score"]), item["explanation"]] for item in risk["indicators"]]] or [["Indicator", "Severity", "Score", "Explanation"], ["None", "-", "0", "No suspicious pattern detected."]])
        heading("Attribution findings")
        table([["Wallet", "Entity/VASP lead", "Confidence", "Reasons"], *[[item["wallet"], item["entity"], f"{item['confidence']}%", "; ".join(item["reasons"])] for item in attributions]] or [["Wallet", "Entity/VASP lead", "Confidence", "Reasons"], ["-", "No seeded match", "-", "Attribution is confidence-based."]])
        heading("Evidence register")
        table([["Evidence ID", "Type", "Reference", "Description"], *[[item.id, item.type, item.transaction_ref or item.wallet_ref or item.hash or "-", item.description or "-"] for item in evidence]])
        heading("Limitations")
        story.append(Paragraph("Demo data is synthetic where applicable. Attribution results are leads/hypotheses with confidence levels, not ownership claims. Blockchain analysis alone does not prove ownership or criminal activity. Findings require investigator validation.", styles["BodyText"]))
        heading("Report metadata")
        table([["Report ID", "Generated", "Version"], [report_id, generated_at.isoformat(), self.VERSION]])
        SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.55 * inch, bottomMargin=0.55 * inch).build(story)

    def list_reports(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            reports = session.query(Report).filter(Report.case_id == case.id).order_by(Report.generated_at.desc()).all()
            return [{"report_id": item.report_id, "case_id": case_id, "generated_at": item.generated_at.isoformat(), "version": item.version, "filename": Path(item.file_path).name if item.file_path else None} for item in reports]