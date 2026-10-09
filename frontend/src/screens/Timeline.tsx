import React from "react";
import { Card, EmptyState } from "../components/BaseComponents";
import { formatCryptoValue, shortHash, type RiskAssessment, type Transaction } from "../api";
import "./Timeline.css";

interface TimelineProps {
  transactions: Transaction[];
  risk?: RiskAssessment;
}

export const Timeline: React.FC<TimelineProps> = ({ transactions, risk }) => {
  const risky = new Set(
    (risk?.indicators || []).flatMap((item) => item.transaction_refs || []),
  );
  const events = [...transactions].sort(
    (left, right) =>
      new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime(),
  );

  if (!events.length) {
    return (
      <EmptyState
        heading="No timeline events"
        description="The timeline is derived from actual transaction timestamps on this case."
      />
    );
  }

  return (
    <div className="timeline">
      <Card>
        <div className="timeline__list">
          {events.map((tx) => (
            <div
              key={tx.tx_hash}
              className={`timeline__item ${risky.has(tx.tx_hash) ? "timeline__item--active" : "timeline__item--complete"}`}
            >
              <div className="timeline__line">
                <div className="timeline__dot" />
              </div>
              <div className="timeline__content">
                <div className="timeline__header">
                  <time className="timeline__time">
                    {new Date(tx.timestamp).toLocaleString()}
                  </time>
                  <h4 className="timeline__event">
                    {shortHash(tx.from)} → {shortHash(tx.to)}
                  </h4>
                </div>
                <p className="timeline__details">
                  {formatCryptoValue(tx.value, tx.token)} · {tx.tx_hash}
                  {tx.chain ? ` · ${tx.chain}` : ""}
                  {risky.has(tx.tx_hash) ? " · flagged by risk rules" : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
