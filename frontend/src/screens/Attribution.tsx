import React from "react";
import { Badge, Card, ConfidenceBadge } from "../components/BaseComponents";
import {
  attributionStrength,
  confidencePercent,
  type Attribution as AttributionRecord,
} from "../api";
import "./Attribution.css";

interface AttributionProps {
  candidates: AttributionRecord[];
}

export const Attribution: React.FC<AttributionProps> = ({ candidates }) => {
  if (!candidates.length) {
    return (
      <Card className="attribution__empty">
        <h3>No reliable attribution</h3>
        <p>
          No evidence-supported VASP/entity match was found for wallets on this case.
          ChainGuard does not invent live exchange attributions.
        </p>
      </Card>
    );
  }

  return (
    <div className="attribution">
      {candidates.map((candidate) => {
        const strength = attributionStrength(candidate.confidence, candidate.status);
        const inferred = (candidate.attribution_type || "").includes("hypothesis") ||
          candidate.provenance === "demo";
        return (
          <Card key={`${candidate.wallet}-${candidate.entity_id}`} className="attribution__primary">
            <div className="attribution__header">
              <div>
                <h3 className="attribution__entity-name">{candidate.entity}</h3>
                <Badge variant="primary">{candidate.entity_type}</Badge>
                <Badge variant={inferred ? "warning" : "success"}>
                  {inferred ? "Unverified inference" : "Evidence-supported"}
                </Badge>
                <Badge variant="neutral">{strength}</Badge>
              </div>
              <ConfidenceBadge confidence={confidencePercent(candidate.confidence)} />
            </div>
            <p>{candidate.explanation}</p>
            <p>
              Wallet: <code>{candidate.wallet}</code> · Source: {candidate.source} · Type:{" "}
              {candidate.attribution_type || "unspecified"} · Status: {candidate.status || "unknown"}
            </p>
            {candidate.reasons?.length > 0 && (
              <div className="attribution__reasons">
                <h4>Reasons</h4>
                <ul>
                  {candidate.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
            {candidate.evidence_refs?.length > 0 && (
              <p>Evidence: {candidate.evidence_refs.join(", ")}</p>
            )}
          </Card>
        );
      })}
    </div>
  );
};
