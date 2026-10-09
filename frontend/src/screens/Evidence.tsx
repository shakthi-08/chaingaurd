import React from "react";
import { Card, EmptyState } from "../components/BaseComponents";
import { formatCryptoValue, type EvidenceItem, type Transaction } from "../api";

interface EvidenceProps {
  items: EvidenceItem[];
  transactions: Transaction[];
}

export const Evidence: React.FC<EvidenceProps> = ({ items, transactions }) => {
  const txMap = new Map(transactions.map((item) => [item.tx_hash, item]));
  if (!items.length) {
    return (
      <EmptyState
        heading="No evidence collected yet"
        description="Evidence is generated from case wallets, transactions, risk indicators, and attribution hypotheses."
      />
    );
  }

  return (
    <div className="attribution">
      {items.map((item) => {
        const tx = item.transaction_ref ? txMap.get(item.transaction_ref) : undefined;
        return (
          <Card key={item.evidence_id}>
            <h4>{item.type}</h4>
            <p>{item.description}</p>
            <p>Source: {item.source || "-"}</p>
            {item.transaction_ref && <p>Transaction: {item.transaction_ref}</p>}
            {tx && (
              <p>
                {tx.from} → {tx.to} · {formatCryptoValue(tx.value, tx.token)} ·{" "}
                {new Date(tx.timestamp).toLocaleString()}
              </p>
            )}
            {item.wallet_ref && <p>Wallet: {item.wallet_ref}</p>}
            {item.timestamp && <p>Timestamp: {new Date(item.timestamp).toLocaleString()}</p>}
            <p>Evidence ID: {item.evidence_id}</p>
          </Card>
        );
      })}
    </div>
  );
};
