import React from 'react';
import { RiskDisplay, Card, Badge, AIInterpretationPanel, ConfidenceBadge, EvidenceCard } from '../components/BaseComponents';
import './RiskAndFraud.css';

interface RiskIndicator {
  type: string;
  severity: string;
  score: number;
  explanation: string;
  transaction_refs?: string[];
}

interface RiskAndFraudProps {
  score: number;
  level: string;
  indicators: RiskIndicator[];
}

export const RiskAndFraud: React.FC<RiskAndFraudProps> = ({
  score,
  level,
  indicators,
}) => {
  return (
    <div className="risk-fraud">
      {/* Risk Hero */}
      <Card className="risk-fraud__hero">
        <div className="risk-fraud__score-container">
          <RiskDisplay
            score={score}
            label={`${score} / 100 — ${level} RISK`}
          />
          <p className="risk-fraud__context">
            Reflects pattern-matching against known typologies, not legal determination.
          </p>
        </div>
      </Card>

      {/* Risk Indicators */}
      <Card className="risk-fraud__indicators">
        <h3>Risk Indicators</h3>
        <div className="risk-fraud__indicators-list">
          {indicators.map((indicator, idx) => (
            <div key={`${indicator.type}-${idx}`} className="risk-fraud__indicator-row">
              <div className="risk-fraud__indicator-header">
                <h4>{indicator.type}</h4>
                <Badge
                  variant={
                    indicator.severity === 'high'
                      ? 'danger'
                      : indicator.severity === 'medium'
                        ? 'warning'
                        : 'success'
                  }
                >
                  {indicator.severity.toUpperCase()}
                </Badge>
              </div>
              <p className="risk-fraud__indicator-explanation">
                {indicator.explanation}
              </p>
              {indicator.transaction_refs && indicator.transaction_refs.length > 0 && (
                <a href="#" className="risk-fraud__evidence-link">
                  {indicator.transaction_refs.length} supporting transaction
                  {indicator.transaction_refs.length !== 1 ? 's' : ''} →
                </a>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Supporting Evidence */}
      <Card className="risk-fraud__evidence">
        <h3>Supporting Evidence</h3>
        <div className="risk-fraud__evidence-list">
          {indicators.slice(0, 3).map((indicator, idx) => (
            <EvidenceCard
              key={`${indicator.type}-${idx}`}
              source={`INDICATOR: ${indicator.type}`}
              excerpt={indicator.explanation}
              link="#"
            />
          ))}
        </div>
      </Card>
    </div>
  );
};
