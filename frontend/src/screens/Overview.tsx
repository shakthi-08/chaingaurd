import React from 'react';
import {
  ArrowRightLeft,
  Network,
  AlertTriangle,
  Target,
  FileText,
  TrendingUp,
} from 'lucide-react';
import { MetricCard, Card, RiskDisplay, AIInterpretationPanel, Button, Badge } from '../components/BaseComponents';
import './Overview.css';

interface OverviewProps {
  hasActiveCase: boolean;
  onStartInvestigation: () => void;
  onOpenWorkspace?: () => void;
  onNavigate?: (screen: string) => void;
  summary?: {
    transactions: number;
    wallets: number;
    hops: number;
    importantPaths: number;
    score: number;
    attribution: number;
    potentialVASPs?: number;
    suspiciousEntities?: number;
  };
  risk?: {
    overall_score: number;
    risk_level: string;
    indicators: any[];
    evidence_refs?: string[];
  };
  recentTransactions?: any[];
  aiSummary?: string;
  error?: string | null;
  health?: { real_mode?: boolean; demo_mode?: boolean; blockchain_provider?: string; operational_chains?: string[] } | null;
  evidenceCount?: number;
  alerts?: Array<{ category: string; severity: string; title: string; explanation: string }>;
  chain?: string;
  caseStatus?: { progress: number; current_stage?: string };
}

export const Overview: React.FC<OverviewProps> = ({
  hasActiveCase,
  onStartInvestigation,
  onOpenWorkspace,
  onNavigate,
  summary,
  risk,
  recentTransactions = [],
  aiSummary,
  health,
  evidenceCount,
  alerts = [],
  chain,
  caseStatus,
}) => {
  const riskScore = risk?.overall_score ?? 0;
  const riskLabel = risk?.risk_level ? risk.risk_level.toUpperCase() : 'UNKNOWN';
  const progress = caseStatus?.progress ?? 0;

  if (!hasActiveCase) {
    return (
      <div className="overview overview--empty">
        <div className="overview__empty-state">
          <div className="overview__empty-icon">🔍</div>
          <h1>No Active Investigation</h1>
          <p>Start a new investigation to analyze blockchain activity</p>
          <Button variant="primary" onClick={onStartInvestigation}>
            Start New Investigation
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="overview">
      {/* Active Investigation Strip */}
      <Card className="overview__active-case">
        <div className="overview__active-header">
          <div className="overview__active-info">
            <h2>Active Investigation</h2>
            <p>
              Chain/network: <strong>{chain || "unknown"}</strong>
              {health?.real_mode ? " · REAL" : health?.demo_mode ? " · DEMO" : ""}
            </p>
          </div>
          <div className="overview__active-actions">
            <Badge variant={riskScore >= 80 ? 'danger' : riskScore >= 50 ? 'warning' : 'primary'}>
              {riskLabel}
            </Badge>
            <Button variant="secondary" size="sm" onClick={onOpenWorkspace}>
              Open Workspace →
            </Button>
          </div>
        </div>
      </Card>

      {/* Metrics Row */}
      <div className="overview__metrics">
        <MetricCard
          label="Transactions Analyzed"
          value={summary?.transactions || 0}
          icon={<ArrowRightLeft size={16} />}
        />
        <MetricCard
          label="Connected Wallets"
          value={summary?.wallets || 0}
          icon={<Network size={16} />}
        />
        <MetricCard
          label="Suspicious Entities"
          value={summary?.suspiciousEntities || 0}
          icon={<AlertTriangle size={16} />}
        />
        <MetricCard
          label="Potential VASPs"
          value={summary?.potentialVASPs || 0}
          icon={<Target size={16} />}
        />
        <MetricCard
          label="Evidence Items"
          value={evidenceCount ?? 0}
          icon={<FileText size={16} />}
        />
        <MetricCard
          label="Investigation Progress"
          value={`${Math.min(100, Math.max(0, progress))}%`}
          icon={<TrendingUp size={16} />}
        />
      </div>

      {/* Risk Summary & Network Preview */}
      <div className="overview__main-section">
        <Card className="overview__risk-summary">
          <h3>Risk Summary</h3>
          <RiskDisplay
            score={riskScore}
            label={`${riskScore} / 100 — ${riskLabel} RISK`}
            className="overview__risk-display"
          />
          <div className="overview__risk-indicators">
            {risk?.indicators?.slice(0, 3).map((indicator, i) => (
              <div key={`${indicator.type}-${i}`} className="overview__indicator">
                <Badge variant="warning">{indicator.type}</Badge>
                <p>{indicator.explanation}</p>
              </div>
            ))}
          </div>
          <button type="button" className="overview__link" onClick={() => onNavigate?.("risk")}>
            View full risk analysis →
          </button>
        </Card>

        <Card className="overview__network-preview">
          <h3>Automated alerts</h3>
          {alerts.length === 0 ? (
            <p>No evidence-supported alerts for this case yet.</p>
          ) : (
            alerts.slice(0, 4).map((alert) => (
              <div key={`${alert.category}-${alert.title}`} className="overview__indicator">
                <Badge variant={alert.severity === "high" ? "danger" : "warning"}>{alert.category}</Badge>
                <p>{alert.title}</p>
              </div>
            ))
          )}
        </Card>

        <Card className="overview__network-preview">
          <h3>Network Preview</h3>
          <div className="overview__network-placeholder">
            <div className="overview__network-icon">🔗</div>
            <p>{summary?.wallets || 0} nodes • {summary?.hops || 0} hops · {health?.real_mode ? "REAL" : "DEMO"}</p>
          </div>
          <button type="button" className="overview__link" onClick={() => onNavigate?.("graph")}>
            Open full graph →
          </button>
        </Card>
      </div>

      {/* Recent Transactions */}
      <Card className="overview__recent-transactions">
        <h3>Recent Transactions</h3>
        <div className="overview__transactions-table">
          <div className="overview__transactions-header">
            <div>Timestamp</div>
            <div>From</div>
            <div>To</div>
            <div>Value</div>
            <div>Risk</div>
          </div>
          {recentTransactions.slice(0, 5).map((tx, i) => (
            <div key={`${tx.tx_hash || tx.from}-${i}`} className="overview__transaction-row">
              <div className="overview__transaction-time">
                {new Date(tx.timestamp).toLocaleTimeString()}
              </div>
              <div>
                <code className="monospace">
                  {tx.from?.slice(0, 8)}...{tx.from?.slice(-6)}
                </code>
              </div>
              <div>
                <code className="monospace">
                  {tx.to?.slice(0, 8)}...{tx.to?.slice(-6)}
                </code>
              </div>
              <div>{tx.value}</div>
              <div>
                <Badge variant="success">
                  OBSERVED
                </Badge>
              </div>
            </div>
          ))}
        </div>
        <button type="button" className="overview__link" onClick={() => onNavigate?.("transactions")}>
          View all transactions →
        </button>
      </Card>

      {/* AI Interpretation */}
      {aiSummary && (
        <AIInterpretationPanel>
          <p>{aiSummary}</p>
          <button type="button" className="overview__link" onClick={() => onNavigate?.("ai")}>
            Open AI Investigation →
          </button>
        </AIInterpretationPanel>
      )}
    </div>
  );
};
