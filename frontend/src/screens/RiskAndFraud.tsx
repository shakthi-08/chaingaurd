import React from "react";
import { Badge, Card, RiskDisplay } from "../components/BaseComponents";
import "./RiskAndFraud.css";

interface RiskIndicator {
  type: string;
  severity: string;
  score: number;
  explanation: string;
  transaction_refs?: string[];
  wallet_addresses?: string[];
  confidence?: number;
}

interface AlertItem {
  category: string;
  severity: string;
  title: string;
  explanation: string;
  wallet_ref?: string | null;
  transaction_ref?: string | null;
}

interface AdvancedBlock {
  defi?: any[];
  bridges?: any[];
  mixers?: any[];
  unknown_contract_label?: string;
}

interface RiskAndFraudProps {
  score: number;
  level: string;
  indicators: RiskIndicator[];
  alerts?: AlertItem[];
  advanced?: AdvancedBlock;
  attributions?: Array<{ entity?: string; confidence?: number; wallet?: string }>;
  chain?: string;
}

export const RiskAndFraud: React.FC<RiskAndFraudProps> = ({
  score,
  level,
  indicators,
  alerts = [],
  advanced,
  attributions = [],
  chain,
}) => {
  const unknown = advanced?.unknown_contract_label || "Unknown Contract";
  return (
    <div className="risk-fraud">
      <Card className="risk-fraud__hero">
        <div className="risk-fraud__score-container">
          <RiskDisplay
            score={score}
            label={`${score} / 100 — ${level} RISK`}
          />
          <p className="risk-fraud__context">
            Deterministic pattern matching on persisted investigation data
            {chain ? ` (${chain})` : ""}. Indicators are investigative leads, not legal findings.
          </p>
        </div>
      </Card>

      <Card className="risk-fraud__indicators">
        <h3>Automated alerts</h3>
        {alerts.length === 0 ? (
          <p>No alerts generated from current analysis results.</p>
        ) : (
          <div className="risk-fraud__indicators-list">
            {alerts.map((alert, idx) => (
              <div key={`${alert.category}-${idx}`} className="risk-fraud__indicator-row">
                <div className="risk-fraud__indicator-header">
                  <h4>{alert.title}</h4>
                  <Badge variant={alert.severity === "high" ? "danger" : alert.severity === "medium" ? "warning" : "success"}>
                    {alert.category}
                  </Badge>
                </div>
                <p className="risk-fraud__indicator-explanation">{alert.explanation}</p>
                {alert.transaction_ref ? <p>Transaction: {alert.transaction_ref}</p> : null}
                {alert.wallet_ref ? <p>Wallet: {alert.wallet_ref}</p> : null}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="risk-fraud__indicators">
        <h3>Advanced indicators</h3>
        <p>DeFi: {(advanced?.defi || []).length} · Bridges: {(advanced?.bridges || []).length} · Mixer: {(advanced?.mixers || []).length}</p>
        {(advanced?.defi || []).map((item: any, idx: number) => (
          <p key={`defi-${idx}`}>DeFi · {item.protocol} ({item.category}) · {item.tx_hash}</p>
        ))}
        {(advanced?.bridges || []).map((item: any, idx: number) => (
          <p key={`br-${idx}`}>
            Bridge · {item.protocol} · {item.chain}
            {item.destination_chain ? ` → ${item.destination_chain}` : ""} · {item.note || "destination unconfirmed"}
          </p>
        ))}
        {(advanced?.mixers || []).map((item: any, idx: number) => (
          <p key={`mx-${idx}`}>Mixer exposure · {item.protocol} · investigative indicator only · {item.tx_hash}</p>
        ))}
        {(advanced?.defi || []).length + (advanced?.bridges || []).length + (advanced?.mixers || []).length === 0 ? (
          <p>No known-protocol matches. Unlabeled contracts remain {unknown}.</p>
        ) : null}
      </Card>

      <Card className="risk-fraud__indicators">
        <h3>VASP attribution</h3>
        {attributions.length === 0 ? (
          <p>No reliable VASP attribution found.</p>
        ) : (
          attributions.map((item, idx) => (
            <p key={`attr-${idx}`}>{item.wallet}: {item.entity} ({item.confidence})</p>
          ))
        )}
      </Card>

      <Card className="risk-fraud__indicators">
        <h3>Triggered indicators</h3>
        {indicators.length === 0 ? (
          <p>No evidence-supported pattern rules triggered on the current case transactions.</p>
        ) : (
          <div className="risk-fraud__indicators-list">
            {indicators.map((indicator, idx) => (
              <div key={`${indicator.type}-${idx}`} className="risk-fraud__indicator-row">
                <div className="risk-fraud__indicator-header">
                  <h4>{indicator.type.replace(/_/g, " ")}</h4>
                  <Badge
                    variant={
                      indicator.severity === "high"
                        ? "danger"
                        : indicator.severity === "medium"
                          ? "warning"
                          : "success"
                    }
                  >
                    {indicator.severity.toUpperCase()}
                  </Badge>
                </div>
                <p>Score contribution: {indicator.score}</p>
                <p className="risk-fraud__indicator-explanation">{indicator.explanation}</p>
                {indicator.transaction_refs?.length ? (
                  <p>{indicator.transaction_refs.length} supporting transaction(s): {indicator.transaction_refs.join(", ")}</p>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
