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

from app.config import is_demo_mode_enabled, is_real_mode_enabled
from app.database import SessionLocal
from app.models import Attribution, Case, Evidence, Finding, GraphEdge, Report, RiskIndicator, Transaction
from app.services.ai_service import AIService
from app.services.attribution_service import AttributionService
from app.services.demo_case_seeder import seed_demo_case
from app.services.transaction_graph_service import TransactionGraphService


class ReportService:
    VERSION = "1.0"
    MAX_TX_ROWS = 40
    MAX_PATH_ROWS = 12
    MAX_EVIDENCE_ROWS = 40

    def __init__(self, session_factory=SessionLocal, output_dir: Path | None = None) -> None:
        self.session_factory = session_factory
        self.output_dir = output_dir or Path(__file__).resolve().parents[2] / "reports"

    @staticmethod
    def _safe(text: Any) -> str:
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def _reported_wallet(case: Case):
        for wallet in case.wallets:
            labels = set(wallet.labels or [])
            if labels & {"seed", "reported"}:
                return wallet
        return case.wallets[0] if case.wallets else None

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
        if case is None and is_demo_mode_enabled() and not is_real_mode_enabled():
            seed_demo_case(self.session_factory)
            with self.session_factory() as session:
                case = session.query(Case).filter(Case.case_id == case_id).first()
        if case is None:
            raise ValueError("Case not found.")

        # Consume persisted investigation data only — do not re-run the pipeline.
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            transactions = self._case_transactions(session, case)
            tx_hashes = [tx.tx_hash for tx in transactions]
            edges = (
                session.query(GraphEdge).filter(GraphEdge.tx_ref.in_(tx_hashes)).all() if tx_hashes else []
            )
            if edges:
                nodes = {edge.source for edge in edges} | {edge.destination for edge in edges}
                graph = {
                    "nodes": [{"id": address, "type": "wallet"} for address in sorted(nodes)],
                    "edges": [
                        {
                            "id": edge.tx_ref,
                            "source": edge.source,
                            "target": edge.destination,
                            "tx_ref": edge.tx_ref,
                            "value": edge.value,
                            "timestamp": edge.timestamp.isoformat(),
                        }
                        for edge in edges
                    ],
                }
            else:
                graph = TransactionGraphService.build_graph(transactions)

            seed = self._reported_wallet(case)
            start_wallet = seed.address if seed else (transactions[0].from_address if transactions else "")
            paths = []
            if start_wallet:
                paths = TransactionGraphService.trace_paths_from_transactions(
                    transactions,
                    start_wallet,
                    max_hops=TransactionGraphService.DEFAULT_MAX_HOPS,
                    max_paths=TransactionGraphService.MAX_PATHS,
                    max_neighbors=TransactionGraphService.MAX_NEIGHBORS_PER_NODE,
                )

            risk_rows = session.query(RiskIndicator).filter(RiskIndicator.case_id == case_id).all()
            finding_rows = session.query(Finding).filter(Finding.case_id == case_id).all()
            if risk_rows or finding_rows:
                indicators = [
                    {
                        "type": item.type,
                        "severity": item.severity,
                        "score": item.score,
                        "explanation": item.explanation,
                    }
                    for item in risk_rows
                ]
                overall = min(100.0, round(sum(item["score"] for item in indicators), 2))
                risk = {
                    "overall_score": overall,
                    "risk_level": "LOW" if overall <= 30 else "MEDIUM" if overall <= 70 else "HIGH",
                    "indicators": indicators,
                }
            else:
                risk = {
                    "overall_score": 0,
                    "risk_level": "LOW",
                    "indicators": [],
                }

            db_attributions = (
                session.query(Attribution)
                .filter(Attribution.wallet_id.in_([w.id for w in case.wallets]))
                .all()
                if case.wallets
                else []
            )
            attributions = [
                {
                    "wallet": item.wallet.address if item.wallet else "-",
                    "entity": item.entity.name if item.entity else "Unknown",
                    "confidence": item.confidence,
                    "reasons": item.reasons or [],
                    "source": item.source,
                    "status": item.status,
                    "attribution_type": item.attribution_type,
                }
                for item in db_attributions
            ]
            evidence = session.query(Evidence).filter(Evidence.case_id == case.id).all()
            reported_wallet = self._reported_wallet(case)
            investigation_depth = max(
                (
                    int(str(label).split(":", 1)[1])
                    for wallet in case.wallets
                    for label in (wallet.labels or [])
                    if str(label).startswith("hop:")
                ),
                default=0,
            )

            try:
                ai_summary = AIService(self.session_factory).summary(case_id)
            except Exception as exc:
                ai_summary = {
                    "answer": f"AI summary is unavailable: {exc}",
                    "provider_status": "unavailable",
                    "ai_assisted": False,
                }

            try:
                from app.services.alert_service import AlertService
                from app.services.protocol_detection_service import ProtocolDetectionService

                alerts = AlertService(self.session_factory).list_case(case_id)
                detections = ProtocolDetectionService.detect_transactions(transactions)
            except Exception:
                alerts = []
                detections = []

            report_id = f"RPT-{hashlib.sha256(f'{case_id}|{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:16]}"
            generated_at = datetime.now(timezone.utc)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{report_id}.pdf"
            try:
                self._write_pdf(
                    output_path,
                    case,
                    transactions,
                    graph,
                    paths,
                    risk,
                    attributions,
                    evidence,
                    report_id,
                    generated_at,
                    reported_wallet=reported_wallet,
                    ai_summary=ai_summary,
                    investigation_depth=investigation_depth,
                    alerts=alerts,
                    detections=detections,
                )
            except Exception as exc:
                raise ValueError(f"Report generation failed: {exc}") from exc
            report = Report(
                report_id=report_id,
                case_id=case.id,
                generated_at=generated_at,
                version=self.VERSION,
                file_path=str(output_path),
            )
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

    def _write_pdf(
        self,
        path,
        case,
        transactions,
        graph,
        paths,
        risk,
        attributions,
        evidence,
        report_id,
        generated_at,
        reported_wallet=None,
        ai_summary=None,
        investigation_depth: int = 0,
        alerts=None,
        detections=None,
    ):
        styles = getSampleStyleSheet()
        disclaimer = (
            "REAL MODE - Deterministic investigative findings based on observed blockchain records"
            if is_real_mode_enabled()
            else "DEMO/SAMPLE - Investigative intelligence, not proof of ownership or criminality"
        )
        story = [
            Paragraph("ChainGuard Investigation Report", styles["Title"]),
            Paragraph(disclaimer, styles["Normal"]),
            Spacer(1, 0.2 * inch),
        ]

        def heading(text):
            story.extend([Spacer(1, 0.12 * inch), Paragraph(text, styles["Heading2"])])

        def table(rows):
            rendered = [[Paragraph(self._safe(cell), styles["BodyText"]) for cell in row] for row in rows]
            item = Table(rendered, repeatRows=1, hAlign="LEFT")
            item.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17343b")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ccd7d7")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f5")]),
                    ]
                )
            )
            story.append(item)

        reported = reported_wallet or self._reported_wallet(case)
        reported_chain = reported.chain if reported else "-"
        heading("Case information")
        table(
            [
                ["Field", "Value"],
                ["Case ID", case.case_id],
                ["Complaint/reference", case.complaint_ref or "-"],
                ["Status", case.status],
                ["Stage", getattr(case, "current_stage", None) or "-"],
                ["Blockchain", reported_chain],
                ["Mode", "REAL" if is_real_mode_enabled() else "DEMO / SYNTHETIC"],
                ["Reported wallet", reported.address if reported else "-"],
                ["Investigation depth", str(investigation_depth)],
                ["Created", case.created_at.isoformat()],
            ]
        )
        heading("Executive summary")
        table(
            [
                ["Measure", "Value"],
                ["Investigation scope", "Persisted normalized transaction activity"],
                ["Transactions analyzed", str(len(transactions))],
                ["Wallets discovered", str(len(graph.get("nodes") or []))],
                ["Hops analyzed", str(max((path["hop_count"] for path in paths), default=0))],
                ["Overall risk", f"{risk['overall_score']}/100 ({risk['risk_level']})"],
                ["Evidence items", str(len(evidence))],
                ["Attribution leads", str(len(attributions))],
            ]
        )
        heading("Transaction summary")
        tx_rows = [
            ["Transaction", "Chain", "From", "To", "Asset", "Block"],
            *[
                [
                    tx.tx_hash,
                    getattr(tx, "chain", None) or "-",
                    tx.from_address,
                    tx.to_address,
                    f"{tx.value} {tx.token or 'native'}",
                    str(getattr(tx, "block", None) or "-"),
                ]
                for tx in transactions[: self.MAX_TX_ROWS]
            ],
        ]
        if len(transactions) > self.MAX_TX_ROWS:
            tx_rows.append(["...", f"{len(transactions) - self.MAX_TX_ROWS} additional omitted", "", "", "", ""])
        table(tx_rows)
        heading("Fund-flow findings")
        table(
            [
                ["Rank", "Path", "Hops", "Total value"],
                *[
                    [str(item.get("rank") or idx), " -> ".join(item["wallets"]), str(item["hop_count"]), item["total_value"]]
                    for idx, item in enumerate(paths[: self.MAX_PATH_ROWS], start=1)
                ],
            ]
            or [["Rank", "Path", "Hops", "Total value"], ["-", "No paths available", "0", "-"]]
        )
        heading("Graph summary")
        table(
            [
                ["Metric", "Value"],
                ["Nodes", str(len(graph.get("nodes") or []))],
                ["Edges", str(len(graph.get("edges") or []))],
            ]
        )
        heading("Risk findings")
        table(
            [
                ["Indicator", "Severity", "Score", "Explanation"],
                *[
                    [item["type"], item["severity"], str(item["score"]), item.get("explanation") or "-"]
                    for item in risk.get("indicators") or []
                ],
            ]
            or [["Indicator", "Severity", "Score", "Explanation"], ["None", "-", "0", "No suspicious pattern detected."]]
        )
        heading("Attribution findings")
        table(
            [
                ["Wallet", "Entity/VASP lead", "Confidence", "Status", "Reasons"],
                *[
                    [
                        item["wallet"],
                        item["entity"],
                        f"{item['confidence']}%",
                        item.get("status") or "-",
                        "; ".join(item.get("reasons") or []),
                    ]
                    for item in attributions
                ],
            ]
            or [
                ["Wallet", "Entity/VASP lead", "Confidence", "Status", "Reasons"],
                ["-", "No verified attribution", "-", "-", "Attribution is evidence-based."],
            ]
        )
        heading("Evidence register")
        table(
            [
                ["Evidence ID", "Type", "Reference", "Description"],
                *[
                    [item.id, item.type, item.transaction_ref or item.wallet_ref or item.hash or "-", item.description or "-"]
                    for item in evidence[: self.MAX_EVIDENCE_ROWS]
                ],
            ]
            or [["Evidence ID", "Type", "Reference", "Description"], ["-", "-", "-", "No evidence collected yet."]]
        )
        heading("AI investigation summary")
        ai_summary = ai_summary or {}
        table(
            [
                ["Field", "Value"],
                ["Provider status", ai_summary.get("provider_status") or "unavailable"],
                ["AI assisted", "yes" if ai_summary.get("ai_assisted") else "no"],
                ["Summary", ai_summary.get("answer") or "AI summary is unavailable. Deterministic analysis remains available."],
            ]
        )
        heading("Detected risk patterns")
        table(
            [
                ["Pattern", "Explanation"],
                *[
                    [item["type"], item.get("explanation") or "-"]
                    for item in risk.get("indicators") or []
                ],
            ]
            or [["Pattern", "Explanation"], ["None observed", "No evidence-supported pattern in persisted data."]]
        )
        heading("DeFi interactions")
        defi_rows = [item for item in (detections or []) if item.get("category") in {"dex", "lending", "staking", "liquidity", "other_defi"}]
        table(
            [
                ["Protocol", "Category", "Transaction", "Chain"],
                *[[item.get("protocol"), item.get("category"), item.get("tx_hash"), item.get("chain")] for item in defi_rows],
            ]
            or [["Protocol", "Category", "Transaction", "Chain"], ["None observed", "-", "-", "-"]]
        )
        heading("Bridge / cross-chain indicators")
        bridge_rows = [item for item in (detections or []) if item.get("category") == "bridge"]
        table(
            [
                ["Bridge", "Source chain", "Destination", "Transaction", "Note"],
                *[
                    [
                        item.get("protocol"),
                        item.get("chain"),
                        item.get("destination_chain") or "unconfirmed",
                        item.get("tx_hash"),
                        item.get("note") or "-",
                    ]
                    for item in bridge_rows
                ],
            ]
            or [["Bridge", "Source chain", "Destination", "Transaction", "Note"], ["None observed", "-", "-", "-", "-"]]
        )
        heading("Mixer indicators")
        mixer_rows = [item for item in (detections or []) if item.get("category") == "mixer"]
        table(
            [
                ["Protocol", "Transaction", "Note"],
                *[
                    [
                        item.get("protocol"),
                        item.get("tx_hash"),
                        "Investigative risk indicator; not a determination of criminal activity",
                    ]
                    for item in mixer_rows
                ],
            ]
            or [["Protocol", "Transaction", "Note"], ["None observed", "-", "-"]]
        )
        heading("Automated alerts")
        table(
            [
                ["Category", "Severity", "Title", "Explanation"],
                *[
                    [item.get("category"), item.get("severity"), item.get("title"), item.get("explanation")]
                    for item in (alerts or [])
                ],
            ]
            or [["Category", "Severity", "Title", "Explanation"], ["None", "-", "-", "No alerts generated from persisted analysis."]]
        )
        heading("Recommended investigative next steps")
        story.append(
            Paragraph(
                "Review supporting transaction hashes, corroborate VASP leads with official channels, "
                "and treat mixer/DeFi/bridge labels as reference matches only. Do not treat this report as legal proof.",
                styles["BodyText"],
            )
        )
        heading("Limitations")
        story.append(
            Paragraph(
                "Demo data is synthetic where applicable. Attribution results are leads/hypotheses with confidence levels, "
                "not ownership claims. Blockchain analysis alone does not prove ownership or criminal activity. "
                "Findings require investigator validation. This report uses persisted case data and does not invent missing facts.",
                styles["BodyText"],
            )
        )
        heading("Report metadata")
        table([["Report ID", "Generated", "Version"], [report_id, generated_at.isoformat(), self.VERSION]])
        SimpleDocTemplate(
            str(path),
            pagesize=letter,
            rightMargin=0.55 * inch,
            leftMargin=0.55 * inch,
            topMargin=0.55 * inch,
            bottomMargin=0.55 * inch,
        ).build(story)

    def list_reports(self, case_id: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            case = session.query(Case).filter(Case.case_id == case_id).first()
            if case is None:
                raise ValueError("Case not found.")
            reports = session.query(Report).filter(Report.case_id == case.id).order_by(Report.generated_at.desc()).all()
            return [
                {
                    "report_id": item.report_id,
                    "case_id": case_id,
                    "generated_at": item.generated_at.isoformat(),
                    "version": item.version,
                    "filename": Path(item.file_path).name if item.file_path else None,
                }
                for item in reports
            ]
