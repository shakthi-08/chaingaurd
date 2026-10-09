import React, { useState } from "react";
import { Button, Card } from "../components/BaseComponents";
import { FileText, Download, Printer } from "lucide-react";
import { attributionStrength, confidencePercent } from "../api";
import "./InvestigationReport.css";

interface InvestigationReportProps {
  caseId?: string;
  walletAddress?: string;
  chain?: string;
  summary?: {
    transactions: number;
    wallets: number;
    hops: number;
    importantPaths: number;
    score: number;
    attribution: number;
  };
  risk?: {
    overall_score: number;
    risk_level: string;
    indicators: any[];
    explanations: string[];
  };
  attributions?: any[];
  recentTransactions?: any[];
  evidence?: any[];
  aiSummary?: string;
  aiStatus?: string;
  realMode?: boolean;
  onExport?: () => Promise<void>;
}

export const InvestigationReport: React.FC<InvestigationReportProps> = ({
  caseId = "",
  walletAddress = "",
  chain = "ethereum",
  summary = {},
  risk = { overall_score: 0, risk_level: "UNKNOWN", indicators: [], explanations: [] },
  attributions = [],
  recentTransactions = [],
  evidence = [],
  aiSummary = "",
  aiStatus,
  realMode = false,
  onExport,
}) => {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleDownloadPDF = async () => {
    if (!onExport || !caseId) {
      setExportError("Report export is unavailable until a case is loaded.");
      return;
    }
    setExporting(true);
    setExportError(null);
    try {
      await onExport();
    } catch (reason) {
      setExportError(reason instanceof Error ? reason.message : "PDF export failed");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="investigation-report">
      <div className="investigation-report__toolbar">
        <div className="investigation-report__title">
          <FileText size={20} />
          <h1>Investigation Report</h1>
        </div>
        <div className="investigation-report__actions">
          <Button variant="secondary" size="sm" onClick={() => window.print()}>
            <Printer size={14} />
            Print
          </Button>
          <Button variant="secondary" size="sm" onClick={handleDownloadPDF} disabled={exporting}>
            <Download size={14} />
            {exporting ? "Generating PDF…" : "Export PDF"}
          </Button>
        </div>
      </div>
      {exportError && <p>{exportError}</p>}

      <div className="investigation-report__content">
        <section className="report-section report-section--header">
          <h1 className="report-title">Blockchain Investigation Report</h1>
          <p>Mode: {realMode ? "REAL blockchain data" : "DEMO / synthetic provider"}</p>
          <p>Case ID: {caseId}</p>
          <p>Reported wallet: {walletAddress}</p>
          <p>Chain: {chain}</p>
          <p>Generated: {new Date().toLocaleString()}</p>
        </section>

        <section className="report-section">
          <h2 className="report-heading">Executive summary</h2>
          <p>Risk {risk.overall_score}/100 ({risk.risk_level})</p>
          <p>Transactions: {summary.transactions || 0}</p>
          <p>Wallets: {summary.wallets || 0}</p>
          <p>Important paths: {summary.importantPaths || 0}</p>
        </section>

        <section className="report-section">
          <h2 className="report-heading">Transactions</h2>
          {recentTransactions.map((tx: any) => (
            <p key={tx.tx_hash}>
              {tx.tx_hash}: {tx.from} → {tx.to} · {tx.value} {tx.token} · {tx.timestamp}
            </p>
          ))}
        </section>

        <section className="report-section">
          <h2 className="report-heading">Risk findings</h2>
          <p>These indicators come from deterministic rules, not ML.</p>
          {(risk.indicators || []).map((indicator: any, index: number) => (
            <p key={`${indicator.type}-${index}`}>
              {indicator.type} ({indicator.severity}): {indicator.explanation}
            </p>
          ))}
        </section>

        <section className="report-section">
          <h2 className="report-heading">Attribution</h2>
          {attributions.length === 0 ? (
            <p>No reliable attribution.</p>
          ) : (
            attributions.map((attr: any) => (
              <p key={attr.entity_id}>
                {attr.entity} · {confidencePercent(attr.confidence)}% ·{" "}
                {attributionStrength(attr.confidence, attr.status)} · {attr.source}
              </p>
            ))
          )}
        </section>

        <section className="report-section">
          <h2 className="report-heading">Evidence</h2>
          {(evidence || []).slice(0, 12).map((item: any) => (
            <p key={item.evidence_id}>
              {item.evidence_id}: {item.type} · {item.description}
            </p>
          ))}
        </section>

        <section className="report-section">
          <h2 className="report-heading">AI summary</h2>
          <p>Provider status: {aiStatus || "not requested"}</p>
          <p>{aiSummary || "No AI summary has been generated for this case yet."}</p>
        </section>

        <section className="report-section">
          <h2 className="report-heading">Limitations</h2>
          <p>
            Attribution is a hypothesis, not proof of ownership. Blockchain analysis alone does not
            prove criminal activity. Demo data is synthetic when not in REAL mode.
          </p>
        </section>
      </div>
    </div>
  );
};
