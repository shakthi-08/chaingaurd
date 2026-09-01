import React from 'react';
import { Card, AIInterpretationPanel, Badge, EvidenceCard } from '../components/BaseComponents';
import './AIInvestigation.css';

interface AIFinding {
  claim: string;
  confidence: number;
  evidence_ref: string;
}

interface AIInvestigationProps {
  interpretation: string;
  findings: AIFinding[];
  explanation?: string;
  isLoading?: boolean;
}

export const AIInvestigation: React.FC<AIInvestigationProps> = ({
  interpretation,
  findings,
  explanation,
  isLoading,
}) => {
  const getConfidenceColor = (conf: number) => {
    if (conf < 0.4) return 'danger';
    if (conf < 0.7) return 'warning';
    return 'success';
  };

  return (
    <div className="ai-investigation">
      {/* Main Interpretation */}
      <AIInterpretationPanel>
        <div className="ai-investigation__content">
          {isLoading ? (
            <p>Analyzing investigation data...</p>
          ) : (
            <>
              <p>{interpretation}</p>
              {explanation && (
                <details className="ai-investigation__details">
                  <summary>Detailed Reasoning</summary>
                  <p>{explanation}</p>
                </details>
              )}
            </>
          )}
        </div>
      </AIInterpretationPanel>

      {/* Key Findings */}
      {!isLoading && findings.length > 0 && (
        <Card className="ai-investigation__findings">
          <h3>Key Findings</h3>
          <div className="ai-investigation__findings-grid">
            {findings.map((finding, idx) => (
              <div key={`${finding.claim}-${idx}`} className="ai-investigation__finding-card">
                <div className="ai-investigation__finding-header">
                  <p className="ai-investigation__finding-claim">
                    {finding.claim}
                  </p>
                  <Badge variant={getConfidenceColor(finding.confidence)}>
                    {Math.round(finding.confidence * 100)}%
                  </Badge>
                </div>
                <a
                  href="#"
                  className="ai-investigation__finding-ref"
                >
                  Based on: {finding.evidence_ref.substring(0, 40)}...
                </a>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Supporting Evidence - Limited Preview */}
      {!isLoading && (
        <Card className="ai-investigation__supporting">
          <h3>Supporting Evidence References</h3>
          <p className="ai-investigation__supporting-intro">
            The following evidence items were examined to generate this interpretation:
          </p>
          <div className="ai-investigation__evidence-list">
            {findings.slice(0, 2).map((finding, idx) => (
              <EvidenceCard
                key={`${finding.evidence_ref}-${idx}`}
                source={`AI EVIDENCE: ${finding.evidence_ref}`}
                excerpt={`Confidence: ${Math.round(finding.confidence * 100)}%`}
                link="#"
              />
            ))}
            {findings.length > 2 && (
              <div className="ai-investigation__evidence-more">
                +{findings.length - 2} more evidence references
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Limitations */}
      <Card className="ai-investigation__limitations">
        <h3>Limitations</h3>
        <ul className="ai-investigation__limitations-list">
          <li>
            This AI interpretation is based on pattern matching and statistical analysis,
            not legal determination
          </li>
          <li>
            AI findings may contain errors and should be verified against source
            transactions
          </li>
          <li>
            This tool assists human investigators but does not replace expert
            judgment
          </li>
        </ul>
      </Card>
    </div>
  );
};
