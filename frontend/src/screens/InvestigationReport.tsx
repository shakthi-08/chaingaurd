import React, { useRef } from 'react';
import { Button, Card } from '../components/BaseComponents';
import { FileText, Download, Printer, Share2 } from 'lucide-react';
import './InvestigationReport.css';

interface InvestigationReportProps {
  caseId?: string;
  walletAddress?: string;
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
  aiSummary?: string;
}

export const InvestigationReport: React.FC<InvestigationReportProps> = ({
  caseId = 'CASE-DEMO-001',
  walletAddress = '0x1111111111111111111111111111111111111111',
  summary = {},
  risk = { overall_score: 0, risk_level: 'UNKNOWN', indicators: [], explanations: [] },
  attributions = [],
  recentTransactions = [],
  aiSummary = '',
}) => {
  const reportRef = useRef<HTMLDivElement>(null);

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPDF = () => {
    // In a real app, this would use a PDF library like pdfkit or react-pdf
    alert('PDF download functionality would be implemented with a PDF library');
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: `ChainGuard Investigation Report - ${caseId}`,
        text: `Investigation report for wallet ${walletAddress}`,
        url: window.location.href,
      });
    } else {
      alert('Report link copied to clipboard');
    }
  };

  const formatDate = (date: Date = new Date()) => {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRiskBadgeClass = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'HIGH':
        return 'badge--danger';
      case 'MEDIUM':
        return 'badge--warning';
      case 'LOW':
        return 'badge--success';
      default:
        return 'badge--neutral';
    }
  };

  return (
    <div className="investigation-report">
      {/* Toolbar */}
      <div className="investigation-report__toolbar">
        <div className="investigation-report__title">
          <FileText size={20} />
          <h1>Investigation Report</h1>
        </div>
        <div className="investigation-report__actions">
          <Button variant="secondary" size="sm" onClick={handlePrint}>
            <Printer size={14} />
            Print
          </Button>
          <Button variant="secondary" size="sm" onClick={handleDownloadPDF}>
            <Download size={14} />
            Export PDF
          </Button>
          <Button variant="secondary" size="sm" onClick={handleShare}>
            <Share2 size={14} />
            Share
          </Button>
        </div>
      </div>

      {/* Report content */}
      <div ref={reportRef} className="investigation-report__content">
        {/* Header */}
        <section className="report-section report-section--header">
          <div className="report-header">
            <h1 className="report-title">Blockchain Investigation Report</h1>
            <div className="report-meta">
              <div className="report-meta-row">
                <span className="report-meta-label">Case ID:</span>
                <code className="report-meta-value">{caseId}</code>
              </div>
              <div className="report-meta-row">
                <span className="report-meta-label">Generated:</span>
                <span className="report-meta-value">{formatDate()}</span>
              </div>
              <div className="report-meta-row">
                <span className="report-meta-label">Status:</span>
                <span className="report-meta-value">Analysis Complete</span>
              </div>
            </div>
          </div>
        </section>

        {/* Executive Summary */}
        <section className="report-section">
          <h2 className="report-heading">Executive Summary</h2>
          <div className="report-summary">
            <div className="summary-card">
              <div className="summary-label">Overall Risk Score</div>
              <div className={`summary-value risk-${risk.risk_level?.toLowerCase()}`}>
                {risk.overall_score || 0} / 100
              </div>
              <div className="summary-level">
                <span className={`badge ${getRiskBadgeClass(risk.risk_level)}`}>
                  {risk.risk_level || 'UNKNOWN'}
                </span>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Transactions Analyzed</div>
              <div className="summary-value">{summary.transactions || 0}</div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Connected Wallets</div>
              <div className="summary-value">{summary.wallets || 0}</div>
            </div>

            <div className="summary-card">
              <div className="summary-label">Suspicious Paths</div>
              <div className="summary-value">{summary.importantPaths || 0}</div>
            </div>
          </div>
        </section>

        {/* Wallet Analysis */}
        <section className="report-section">
          <h2 className="report-heading">Wallet Analysis</h2>
          <div className="report-field">
            <div className="report-label">Reported Address</div>
            <code className="report-code">{walletAddress}</code>
          </div>
          <div className="report-paragraph">
            This wallet was analyzed across the blockchain to identify transaction patterns,
            fund flows, and associated entities. The analysis included chain hops, value
            transfers, and temporal patterns to establish risk and attribution.
          </div>
        </section>

        {/* Fund Flow */}
        <section className="report-section">
          <h2 className="report-heading">Fund Flow Analysis</h2>
          <div className="report-paragraph">
            {summary.importantPaths || 0} distinct fund flow paths were identified from the
            reported wallet. Paths were analyzed for:
          </div>
          <ul className="report-list">
            <li>Intermediary involvement and VASP detection</li>
            <li>Transaction values and temporal clustering</li>
            <li>Wallet address reuse patterns</li>
            <li>Bridge service activity (cross-chain)</li>
          </ul>
        </section>

        {/* Network Analysis */}
        <section className="report-section">
          <h2 className="report-heading">Network Analysis</h2>
          <div className="report-paragraph">
            Graph analysis identified {summary.wallets || 0} wallets in the transaction
            network and their interconnections. Network metrics include:
          </div>
          <ul className="report-list">
            <li>Node clustering and community detection</li>
            <li>Betweenness centrality (influential nodes)</li>
            <li>Path length and hop distance</li>
            <li>Entity concentration and exchange proximity</li>
          </ul>
        </section>

        {/* Risk Assessment */}
        <section className="report-section">
          <h2 className="report-heading">Risk Assessment</h2>
          <div className="risk-breakdown">
            <div className="risk-item">
              <div className="risk-label">Overall Score</div>
              <div className="risk-bar">
                <div
                  className="risk-bar-fill"
                  style={{
                    width: `${Math.min(risk.overall_score || 0, 100)}%`,
                  }}
                />
              </div>
              <div className="risk-value">{risk.overall_score || 0}/100</div>
            </div>
          </div>

          {risk.indicators && risk.indicators.length > 0 && (
            <div className="report-subsection">
              <h3 className="report-subheading">Risk Indicators</h3>
              <ul className="risk-indicators">
                {risk.indicators.slice(0, 5).map((indicator, index) => (
                  <li key={index} className="risk-indicator">
                    <span className="indicator-type">{indicator.type}</span>
                    <span className={`indicator-severity severity-${indicator.severity?.toLowerCase()}`}>
                      {indicator.severity?.toUpperCase()}
                    </span>
                    <span className="indicator-explanation">{indicator.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        {/* Attribution */}
        <section className="report-section">
          <h2 className="report-heading">Entity Attribution</h2>
          {attributions && attributions.length > 0 ? (
            <div className="attribution-list">
              {attributions.slice(0, 3).map((attr, index) => (
                <div key={index} className="attribution-item">
                  <div className="attribution-entity">{attr.entity}</div>
                  <div className="attribution-meta">
                    <span>Type: {attr.entity_type}</span>
                    <span>Confidence: {(attr.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="attribution-reason">{attr.explanation}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="report-paragraph">No entity attributions available.</div>
          )}
        </section>

        {/* AI Investigation Findings */}
        {aiSummary && (
          <section className="report-section">
            <h2 className="report-heading">AI Investigation Summary</h2>
            <div className="ai-finding">
              <div className="ai-marker">AI-Assisted Analysis</div>
              <div className="report-paragraph">{aiSummary}</div>
            </div>
          </section>
        )}

        {/* Evidence & Methodology */}
        <section className="report-section">
          <h2 className="report-heading">Evidence & Methodology</h2>
          <div className="report-paragraph">
            This investigation employed the following data sources and analytical methods:
          </div>
          <ul className="report-list">
            <li>On-chain transaction data from blockchain records</li>
            <li>Known VASP and exchange address databases</li>
            <li>AI-assisted pattern analysis and anomaly detection</li>
            <li>Temporal correlation and fund flow tracking</li>
            <li>Attribution confidence scoring based on supporting evidence</li>
          </ul>
        </section>

        {/* Timeline */}
        <section className="report-section">
          <h2 className="report-heading">Investigation Timeline</h2>
          <div className="timeline-compact">
            <div className="timeline-item">
              <div className="timeline-time">Investigation Started</div>
              <div className="timeline-event">Data ingestion and wallet analysis initiated</div>
            </div>
            <div className="timeline-item">
              <div className="timeline-time">Blockchain Analysis</div>
              <div className="timeline-event">On-chain transactions retrieved and normalized</div>
            </div>
            <div className="timeline-item">
              <div className="timeline-time">Fund Flow Tracing</div>
              <div className="timeline-event">Paths and flows identified across network</div>
            </div>
            <div className="timeline-item">
              <div className="timeline-time">Risk Scoring</div>
              <div className="timeline-event">Risk assessment calculated and validated</div>
            </div>
            <div className="timeline-item active">
              <div className="timeline-time">Report Generated</div>
              <div className="timeline-event">Investigation findings compiled</div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <section className="report-section report-section--footer">
          <div className="report-footer">
            <p className="footer-disclaimer">
              This report contains sensitive investigation information. Unauthorized distribution
              is prohibited. Generated by ChainGuard Blockchain Forensics Platform.
            </p>
            <p className="footer-notice">
              Investigation Case ID: <code>{caseId}</code>
            </p>
          </div>
        </section>
      </div>
    </div>
  );
};
