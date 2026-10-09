import React, { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  ReactFlowProvider,
  type Edge,
  type Node,
  useReactFlow,
} from "reactflow";
import { Badge, Button, Card, Drawer } from "../components/BaseComponents";
import {
  attributionStrength,
  confidencePercent,
  formatCryptoValue,
  shortHash,
  type Attribution,
  type CaseWallet,
  type Graph,
  type RiskAssessment,
} from "../api";
import { Network } from "lucide-react";
import "./InvestigationGraph.css";

interface InvestigationGraphProps {
  graph?: Graph;
  attributions?: Attribution[];
  risk?: RiskAssessment;
  seedWallet?: string;
  wallets?: CaseWallet[];
  loading?: boolean;
  error?: string | null;
}

const hopDistance = (
  seed: string,
  edges: { source: string; target: string }[],
) => {
  const distance = new Map<string, number>();
  distance.set(seed.toLowerCase(), 0);
  const queue = [seed.toLowerCase()];
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    const source = edge.source.toLowerCase();
    const target = edge.target.toLowerCase();
    adjacency.set(source, [...(adjacency.get(source) || []), target]);
    adjacency.set(target, [...(adjacency.get(target) || []), source]);
  }
  while (queue.length) {
    const current = queue.shift()!;
    for (const next of adjacency.get(current) || []) {
      if (distance.has(next)) continue;
      distance.set(next, (distance.get(current) || 0) + 1);
      queue.push(next);
    }
  }
  return distance;
};

const layoutNodes = (
  nodeIds: string[],
  edges: { source: string; target: string }[],
  seed: string,
) => {
  const distances = hopDistance(seed || nodeIds[0] || "", edges);
  const layers = new Map<number, string[]>();
  for (const id of nodeIds) {
    const layer = distances.get(id.toLowerCase()) ?? 99;
    layers.set(layer, [...(layers.get(layer) || []), id]);
  }
  const positions = new Map<string, { x: number; y: number }>();
  const sortedLayers = [...layers.keys()].sort((a, b) => a - b);
  sortedLayers.forEach((layer, layerIndex) => {
    const ids = layers.get(layer) || [];
    ids.forEach((id, index) => {
      const offset = ((ids.length - 1) / 2) * 110;
      positions.set(id, {
        x: 80 + layerIndex * 280,
        y: 80 + index * 110 - offset + 200,
      });
    });
  });
  return positions;
};

export const InvestigationGraph: React.FC<InvestigationGraphProps> = (props) => (
  <ReactFlowProvider>
    <InvestigationGraphCanvas {...props} />
  </ReactFlowProvider>
);

const InvestigationGraphCanvas: React.FC<InvestigationGraphProps> = ({
  graph,
  attributions = [],
  risk,
  seedWallet = "",
  wallets = [],
  loading,
  error,
}) => {
  const { fitView } = useReactFlow();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [filterType, setFilterType] = useState("all");

  const seed =
    wallets.find((item) => item.is_seed)?.address || seedWallet.toLowerCase();
  const attributionMap = useMemo(
    () => new Map(attributions.map((item) => [item.wallet.toLowerCase(), item])),
    [attributions],
  );
  const riskyWallets = useMemo(() => {
    const set = new Set<string>();
    for (const indicator of risk?.indicators || []) {
      for (const address of indicator.wallet_addresses || []) {
        set.add(address.toLowerCase());
      }
    }
    return set;
  }, [risk]);

  const classify = useCallback(
    (address: string) => {
      const attr = attributionMap.get(address.toLowerCase());
      if (address.toLowerCase() === seed.toLowerCase()) return "seed";
      const graphType = graph?.nodes?.find((item) => item.id.toLowerCase() === address.toLowerCase())?.type;
      if (graphType === "bridge") return "bridge";
      if (graphType === "mixer") return "mixer";
      if (graphType === "defi") return "defi";
      if (
        attr &&
        ["vasp", "exchange", "custodial_service"].includes(
          String(attr.entity_type || "").toLowerCase(),
        )
      ) {
        return "vasp";
      }
      if (riskyWallets.has(address.toLowerCase()) || (risk?.overall_score || 0) >= 70) {
        if (riskyWallets.has(address.toLowerCase())) return "high-risk";
      }
      if (attr) return "entity";
      return "intermediary";
    },
    [attributionMap, graph?.nodes, risk?.overall_score, riskyWallets, seed],
  );

  const colorFor = (kind: string) => {
    switch (kind) {
      case "seed":
        return "#7c5cff";
      case "vasp":
        return "#2ec4b6";
      case "bridge":
        return "#3d8bfd";
      case "defi":
        return "#8b5cf6";
      case "mixer":
        return "#fb7185";
      case "high-risk":
        return "#f0473e";
      case "entity":
        return "#f0b429";
      default:
        return "#5b8def";
    }
  };

  const distances = useMemo(
    () => hopDistance(seed, graph?.edges || []),
    [graph?.edges, seed],
  );

  const { nodes, edges } = useMemo(() => {
    if (!graph?.nodes?.length) return { nodes: [] as Node[], edges: [] as Edge[] };
    const positions = layoutNodes(
      graph.nodes.map((item) => item.id),
      graph.edges || [],
      seed,
    );
    const flowNodes: Node[] = graph.nodes
      .filter((item) => {
        const kind = classify(item.id);
        return filterType === "all" || kind === filterType;
      })
      .map((item) => {
        const kind = classify(item.id);
        const attr = attributionMap.get(item.id.toLowerCase());
        const label = attr?.entity
          ? attr.entity
          : `${item.id.slice(0, 6)}…${item.id.slice(-4)}`;
        return {
          id: item.id,
          data: { label: `${kind === "seed" ? "SEED " : ""}${label}` },
          position: positions.get(item.id) || { x: 0, y: 0 },
          style: {
            background: colorFor(kind),
            color: "#0b1020",
            border: selectedNode === item.id ? "3px solid #fff" : "2px solid transparent",
            borderRadius: 8,
            padding: 8,
            fontSize: 11,
            fontWeight: 700,
            minWidth: 120,
            textAlign: "center",
          },
        };
      });

    const visible = new Set(flowNodes.map((item) => item.id));
    const flowEdges: Edge[] = (graph.edges || [])
      .filter((item) => visible.has(item.source) && visible.has(item.target))
      .map((item) => {
          const hop = distances.get(item.target.toLowerCase());
          const relation = item.relation_type ? ` · ${item.relation_type}` : "";
          const label = `${formatCryptoValue(item.value, item.token)} · ${shortHash(item.tx_ref, 4)}${hop != null ? ` · hop ${hop}` : ""}${relation}`;
        return {
          id: item.id,
          source: item.source,
          target: item.target,
          label,
          markerEnd: { type: MarkerType.ArrowClosed, color: "#9aa4b2" },
          style: {
            stroke: selectedEdge === item.id ? "#7c5cff" : "#9aa4b2",
            strokeWidth: selectedEdge === item.id ? 3 : 1.5,
          },
        };
      });
    return { nodes: flowNodes, edges: flowEdges };
  }, [
    attributionMap,
    classify,
    distances,
    filterType,
    graph,
    seed,
    selectedEdge,
    selectedNode,
  ]);

  const selectedNodeData = selectedNode
    ? {
        address: selectedNode,
        kind: classify(selectedNode),
        attribution: attributionMap.get(selectedNode.toLowerCase()),
        hop: distances.get(selectedNode.toLowerCase()),
        wallet: wallets.find(
          (item) => item.address.toLowerCase() === selectedNode.toLowerCase(),
        ),
      }
    : null;
  const selectedEdgeData = selectedEdge
    ? (graph?.edges || []).find((item) => item.id === selectedEdge)
    : null;

  if (loading && !graph?.nodes?.length) {
    return (
      <div className="investigation-graph">
        <div className="investigation-graph__empty">
          <Network size={48} />
          <h3>Building investigation graph</h3>
          <p>Loading wallets and transactions for this case.</p>
        </div>
      </div>
    );
  }

  if (!graph?.nodes?.length) {
    return (
      <div className="investigation-graph">
        <div className="investigation-graph__empty">
          <Network size={48} />
          <h3>No graph data yet</h3>
          <p>
            {error ||
              "Ingest a wallet to generate the investigation graph from actual case transactions."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="investigation-graph">
      <div className="investigation-graph__toolbar">
        <div className="investigation-graph__toolbar-group">
          <label className="investigation-graph__filter-label">Filter</label>
          <select
            value={filterType}
            onChange={(event) => setFilterType(event.target.value)}
            className="investigation-graph__filter-select"
          >
            <option value="all">All nodes</option>
            <option value="seed">Reported wallet</option>
            <option value="intermediary">Intermediaries</option>
            <option value="vasp">VASP / exchange</option>
            <option value="bridge">Bridge</option>
            <option value="defi">DeFi protocol</option>
            <option value="mixer">Mixer</option>
            <option value="high-risk">High risk</option>
            <option value="entity">Attributed entity</option>
          </select>
        </div>
        <Button variant="secondary" size="sm" onClick={() => fitView({ padding: 0.2 })}>
          Fit / reset
        </Button>
      </div>

      <Card className="investigation-graph__canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.2}
          maxZoom={2}
          onNodeClick={(_, node) => {
            setSelectedEdge(null);
            setSelectedNode(node.id);
          }}
          onEdgeClick={(_, edge) => {
            setSelectedNode(null);
            setSelectedEdge(edge.id);
          }}
        >
          <Background color="var(--border-subtle)" gap={16} />
          <Controls />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </Card>

      <div className="investigation-graph__legend">
        <div className="investigation-graph__legend-row">
          <div className="investigation-graph__legend-item">
            <div className="investigation-graph__legend-node" style={{ background: colorFor("seed") }} />
            <span>Reported / seed wallet</span>
          </div>
          <div className="investigation-graph__legend-item">
            <div className="investigation-graph__legend-node" style={{ background: colorFor("intermediary") }} />
            <span>Intermediary</span>
          </div>
          <div className="investigation-graph__legend-item">
            <div className="investigation-graph__legend-node" style={{ background: colorFor("vasp") }} />
            <span>VASP / exchange</span>
          </div>
          <div className="investigation-graph__legend-item">
            <div className="investigation-graph__legend-node" style={{ background: colorFor("high-risk") }} />
            <span>High-risk wallet</span>
          </div>
        </div>
      </div>

      <Drawer
        isOpen={Boolean(selectedNode || selectedEdge)}
        onClose={() => {
          setSelectedNode(null);
          setSelectedEdge(null);
        }}
        title={selectedEdge ? "Transaction" : "Wallet"}
      >
        {selectedNodeData && (
          <div className="investigation-graph__detail">
            <div className="investigation-graph__detail-section">
              <h4>Address</h4>
              <code className="investigation-graph__detail-code">{selectedNodeData.address}</code>
            </div>
            <div className="investigation-graph__detail-section">
              <h4>Role</h4>
              <Badge variant={selectedNodeData.kind === "high-risk" ? "danger" : "primary"}>
                {selectedNodeData.kind}
              </Badge>
              {selectedNodeData.hop != null && <p>Hop from reported wallet: {selectedNodeData.hop}</p>}
              {selectedNodeData.wallet?.chain && <p>Chain: {selectedNodeData.wallet.chain}</p>}
            </div>
            {selectedNodeData.attribution ? (
              <div className="investigation-graph__detail-section">
                <h4>Attribution</h4>
                <p>{selectedNodeData.attribution.entity}</p>
                <p>
                  {confidencePercent(selectedNodeData.attribution.confidence)}% ·{" "}
                  {attributionStrength(
                    selectedNodeData.attribution.confidence,
                    selectedNodeData.attribution.status,
                  )}
                </p>
                <p>{selectedNodeData.attribution.source}</p>
              </div>
            ) : (
              <p>No reliable attribution for this wallet.</p>
            )}
          </div>
        )}
        {selectedEdgeData && (
          <div className="investigation-graph__detail">
            <div className="investigation-graph__detail-section">
              <h4>Hash</h4>
              <code className="investigation-graph__detail-code">{selectedEdgeData.tx_ref}</code>
            </div>
            <p>From: {selectedEdgeData.source}</p>
            <p>To: {selectedEdgeData.target}</p>
            <p>Amount: {formatCryptoValue(selectedEdgeData.value, selectedEdgeData.token)}</p>
            <p>Time: {new Date(selectedEdgeData.timestamp).toLocaleString()}</p>
            {selectedEdgeData.chain && <p>Chain: {selectedEdgeData.chain}</p>}
          </div>
        )}
      </Drawer>
    </div>
  );
};
