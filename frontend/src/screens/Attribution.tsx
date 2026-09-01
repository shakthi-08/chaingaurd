import React from 'react';
import { Card, Badge, ConfidenceBadge, EvidenceCard } from '../components/BaseComponents';
import './Attribution.css';

interface AttributionCandidate {
  entity: string;
  entity_type: string;
  confidence: number;
  reasons: string[];
  evidence_refs: string[];
  explanation: string;
}

interface AttributionProps {
  candidates: AttributionCandidate[];
}

export const Attribution: React.FC<AttributionProps> = ({ candidates }) => {
  return (
    <div className="attribution">
      {candidates.length > 0 ? (
        <>
          {/* Primary Attribution */}
          <Card className="attribution__primary">
            <div className="attribution__header">
              <div>
                <h3 className="attribution__entity-name">
                  {candidates[0].entity}
                </h3>
                <Badge variant="primary">{candidates[0].entity_type}</Badge>
              </div>
              <div className="attribution__confidence">
                <ConfidenceBadge confidence={candidates[0].confidence} />
              </div>
            </div>

            <div className="attribution__explanation">
              <p>{candidates[0].explanation}</p>
            </div>

            {candidates[0].reasons.length > 0 && (
              <div className="attribution__reasons">
                <h4>Supporting Indicators</h4>
                <ul>
                  {candidates[0].reasons.map((reason, idx) => (
                    <li key={`${reason}-${idx}`}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>

          {/* Evidence */}
          {candidates[0].evidence_refs.length > 0 && (
            <Card className="attribution__evidence">
              <h3>Supporting Evidence</h3>
              <div className="attribution__evidence-list">
                {candidates[0].evidence_refs.map((ref, idx) => (
                  <EvidenceCard
                    key={`${ref}-${idx}`}
                    source={`EVIDENCE: ${ref.split('_')[0]}`}
                    excerpt={`Referenced in transaction analysis as evidence for ${candidates[0].entity_type}`}
                    link="#"
                  />
                ))}
              </div>
            </Card>
          )}

          {/* Alternative Candidates */}
          {candidates.length > 1 && (
            <Card className="attribution__alternatives">
              <h3>Alternative Candidates</h3>
              <div className="attribution__candidates-list">
                {candidates.slice(1).map((candidate, idx) => (
                  <div key={`${candidate.entity}-${idx}`} className="attribution__candidate">
                    <div className="attribution__candidate-header">
                      <div>
                        <h4>{candidate.entity}</h4>
                        <Badge variant="neutral">{candidate.entity_type}</Badge>
                      </div>
                      <ConfidenceBadge confidence={candidate.confidence} />
                    </div>
                    <p className="attribution__candidate-explanation">
                      {candidate.explanation}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      ) : (
        <Card className="attribution__empty">
          <p>No attribution data available yet. Analysis in progress...</p>
        </Card>
      )}
    </div>
  );
};
