import React, { useMemo, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import { Badge, Card, EmptyState } from '../components/BaseComponents';
import { Wallet, ArrowRight } from 'lucide-react';
import './FundFlow.css';

interface FundFlowProps {
  paths?: Array<{
    rank: number;
    start_wallet: string;
    end_wallet: string;
    wallets: string[];
    transactions: string[];
    hop_count: number;
    total_value: string;
    values: string[];
    timestamps: string[];
  }>;
  risk?: {
    overall_score: number;
    risk_level: string;
  };
}

export const FundFlow: React.FC<FundFlowProps> = ({ paths = [], risk }) => {
  const [selectedPath, setSelectedPath] = useState<number | null>(null);

  // Build ReactFlow nodes and edges from paths
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!paths || paths.length === 0) {
      return { nodes: [], edges: [] };
    }

    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const nodeSet = new Set<string>();

    paths.forEach((path, pathIndex) => {
      const wallets = path.wallets || [];
      
      // Create nodes for each wallet in the path
      wallets.forEach((wallet, walletIndex) => {
        if (!nodeSet.has(wallet)) {
          nodeSet.add(wallet);
          
          // Determine node type and color based on position and risk
          let nodeType = 'normal';
          let bgColor = 'var(--surface-2)';
          let borderColor = 'var(--border-subtle)';
          
          if (walletIndex === 0) {
            nodeType = 'source';
            borderColor = 'var(--accent-primary)';
          } else if (walletIndex === wallets.length - 1) {
            nodeType = 'target';
            borderColor = 'var(--success)';
          } else {
            borderColor = 'var(--warning)';
          }

          nodes.push({
            id: wallet,
            data: {
              label: (
                <div className="fund-flow__node">
                  <Wallet size={16} />
                  <code>{wallet.slice(0, 8)}...{wallet.slice(-6)}</code>
                </div>
              ),
            },
            position: {
              x: walletIndex * 200,
              y: pathIndex * 100,
            },
            style: {
              background: bgColor,
              border: `2px solid ${borderColor}`,
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '12px',
              color: 'var(--text-primary)',
              fontFamily: 'IBM Plex Mono, monospace',
            },
          });
        }
      });

      // Create edges between wallets in path
      for (let i = 0; i < wallets.length - 1; i++) {
        const fromWallet = wallets[i];
        const toWallet = wallets[i + 1];
        const txValue = path.values?.[i] || '0';
        const edgeKey = `${fromWallet}->${toWallet}-${pathIndex}`;

        // Scale edge width based on value (simple heuristic)
        let strokeWidth = 2;
        try {
          const valueNum = parseFloat(txValue);
          if (valueNum > 1000) strokeWidth = 4;
          else if (valueNum > 100) strokeWidth = 3;
        } catch {
          // keep default
        }

        // Color based on risk level
        let edgeColor = 'var(--success)';
        if (risk?.risk_level === 'HIGH') {
          edgeColor = 'var(--danger)';
        } else if (risk?.risk_level === 'MEDIUM') {
          edgeColor = 'var(--warning)';
        }

        edges.push({
          id: edgeKey,
          source: fromWallet,
          target: toWallet,
          label: (
            <span className="fund-flow__edge-label" title={txValue}>
              {parseFloat(txValue) > 1000 ? `${(parseFloat(txValue) / 1000).toFixed(1)}K` : `${txValue.slice(0, 8)}`}
            </span>
          ),
          markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
          style: {
            stroke: edgeColor,
            strokeWidth,
            opacity: selectedPath === pathIndex ? 1 : 0.5,
          },
          animated: selectedPath === pathIndex,
        });
      }
    });

    return { nodes, edges };
  }, [paths, selectedPath, risk?.risk_level]);

  if (!paths || paths.length === 0) {
    return (
      <div className="fund-flow">
        <EmptyState
          icon={<ArrowRight size={48} />}
          heading="No fund flow data available"
          description="Paths will appear once blockchain analysis completes"
        />
      </div>
    );
  }

  return (
    <div className="fund-flow">
      <div className="fund-flow__header">
        <h2>Fund Flow Analysis</h2>
        <p className="fund-flow__subtitle">
          Directional wallet movement and transaction paths
        </p>
      </div>

      {/* Path selector pills */}
      <div className="fund-flow__paths">
        {paths.map((path, index) => (
          <button
            key={`${path.start_wallet}-${path.end_wallet}-${index}`}
            className={`fund-flow__path-pill ${
              selectedPath === index ? 'fund-flow__path-pill--active' : ''
            }`}
            onClick={() => setSelectedPath(selectedPath === index ? null : index)}
          >
            <span className="fund-flow__path-number">Path {index + 1}</span>
            <span className="fund-flow__path-hops">{path.hop_count} hops</span>
            <Badge
              variant={
                parseFloat(path.total_value) > 10000
                  ? 'danger'
                  : parseFloat(path.total_value) > 1000
                    ? 'warning'
                    : 'success'
              }
            >
              {parseFloat(path.total_value).toLocaleString('en-US', {
                maximumFractionDigits: 0,
              })}
            </Badge>
          </button>
        ))}
      </div>

      {/* ReactFlow graph */}
      <Card className="fund-flow__canvas">
        <ReactFlow nodes={flowNodes} edges={flowEdges}>
          <Background color="var(--border-subtle)" gap={16} />
          <Controls />
        </ReactFlow>
      </Card>

      {/* Legend */}
      <div className="fund-flow__legend">
        <div className="fund-flow__legend-item">
          <div className="fund-flow__legend-box" style={{ borderColor: 'var(--accent-primary)' }} />
          <span>Source Wallet</span>
        </div>
        <div className="fund-flow__legend-item">
          <div className="fund-flow__legend-box" style={{ borderColor: 'var(--warning)' }} />
          <span>Intermediary</span>
        </div>
        <div className="fund-flow__legend-item">
          <div className="fund-flow__legend-box" style={{ borderColor: 'var(--success)' }} />
          <span>Destination</span>
        </div>
        <div className="fund-flow__legend-item">
          <div className="fund-flow__legend-line" style={{ borderTopWidth: '2px' }} />
          <span>Low Value</span>
        </div>
        <div className="fund-flow__legend-item">
          <div className="fund-flow__legend-line" style={{ borderTopWidth: '4px' }} />
          <span>High Value</span>
        </div>
      </div>
    </div>
  );
};
