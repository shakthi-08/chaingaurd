import React, { useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from "reactflow";
import { Badge, Card, EmptyState } from "../components/BaseComponents";
import { formatCryptoValue, shortHash, type Path, type RiskAssessment, type Transaction } from "../api";
import { ArrowRight } from "lucide-react";
import "./FundFlow.css";

interface FundFlowProps {
  paths?: Path[];
  transactions?: Transaction[];
  risk?: RiskAssessment;
  seedWallet?: string;
}

export const FundFlow: React.FC<FundFlowProps> = ({
  paths = [],
  transactions = [],
  seedWallet = "",
}) => {
  const [selectedPath, setSelectedPath] = useState<number | null>(0);
  const txMap = useMemo(
    () => new Map(transactions.map((item) => [item.tx_hash, item])),
    [transactions],
  );

  const { nodes, edges } = useMemo(() => {
    const path = selectedPath != null ? paths[selectedPath] : paths[0];
    if (!path) return { nodes: [] as Node[], edges: [] as Edge[] };
    const flowNodes: Node[] = path.wallets.map((wallet, index) => ({
      id: wallet,
      data: {
        label:
          index === 0 && wallet.toLowerCase() === seedWallet.toLowerCase()
            ? `SEED ${shortHash(wallet)}`
            : shortHash(wallet),
      },
      position: { x: index * 220, y: 80 },
      style: {
        background: index === 0 ? "#7c5cff" : index === path.wallets.length - 1 ? "#2ec4b6" : "#f0b429",
        color: "#0b1020",
        borderRadius: 8,
        padding: 8,
        fontWeight: 700,
      },
    }));
    const flowEdges: Edge[] = [];
    for (let index = 0; index < path.wallets.length - 1; index += 1) {
      const hash = path.transactions[index];
      const tx = hash ? txMap.get(hash) : undefined;
      const value = tx?.value || path.values[index] || "0";
      const token = tx?.token || null;
      flowEdges.push({
        id: `${path.rank}-${hash || index}`,
        source: path.wallets[index],
        target: path.wallets[index + 1],
        label: `${formatCryptoValue(value, token)} · ${shortHash(hash || "", 4)}`,
        markerEnd: { type: MarkerType.ArrowClosed },
      });
    }
    return { nodes: flowNodes, edges: flowEdges };
  }, [paths, seedWallet, selectedPath, txMap]);

  if (!paths.length) {
    return (
      <div className="fund-flow">
        <EmptyState
          icon={<ArrowRight size={48} />}
          heading="No fund-flow paths yet"
          description="Paths are built from ingested case transactions. Increase investigation depth to follow counterparties."
        />
      </div>
    );
  }

  const active = selectedPath != null ? paths[selectedPath] : paths[0];

  return (
    <div className="fund-flow">
      <div className="fund-flow__header">
        <h2>Fund Flow Analysis</h2>
        <p className="fund-flow__subtitle">
          Directed paths from the reported wallet using actual transaction amounts and hashes.
        </p>
      </div>

      <div className="fund-flow__paths">
        {paths.slice(0, 8).map((path, index) => (
          <button
            key={`${path.rank}-${path.end_wallet}`}
            className={`fund-flow__path-pill ${selectedPath === index ? "fund-flow__path-pill--active" : ""}`}
            onClick={() => setSelectedPath(index)}
          >
            <span className="fund-flow__path-number">Path {path.rank}</span>
            <span className="fund-flow__path-hops">{path.hop_count} hop{path.hop_count === 1 ? "" : "s"}</span>
            <Badge variant="primary">{formatCryptoValue(path.total_value)}</Badge>
          </button>
        ))}
      </div>

      <Card className="fund-flow__canvas">
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background color="var(--border-subtle)" gap={16} />
          <Controls />
        </ReactFlow>
      </Card>

      {active && (
        <Card>
          <h3>Selected path</h3>
          <p>{active.wallets.map((wallet) => shortHash(wallet)).join(" → ")}</p>
          <ul>
            {active.transactions.map((hash, index) => {
              const tx = txMap.get(hash);
              return (
                <li key={hash}>
                  {hash} · {formatCryptoValue(tx?.value || active.values[index], tx?.token)} ·{" "}
                  {tx?.timestamp ? new Date(tx.timestamp).toLocaleString() : active.timestamps[index]}
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
};
