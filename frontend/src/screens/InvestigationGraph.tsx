import React, { useMemo, useState, useCallback } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import { Card, Badge, Button, Drawer } from '../components/BaseComponents';
import { Network, Filter, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import './InvestigationGraph.css';

interface GraphNode {
  id: string;
  type?: string;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  tx_ref: string;
  value: string;
  timestamp: string;
  token?: string;
}

interface InvestigationGraphProps {
  graph?: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    transactions?: GraphEdge[];
  };
  attributions?: Array<{
    wallet: string;
    entity: string;
    entity_type: string;
    confidence: number;
  }>;
  risk?: {
    overall_score: number;
    risk_level: string;
  };
}

const getNodeColor = (nodeType?: string): string => {
  switch (nodeType?.toLowerCase()) {
    case 'suspect':
      return 'var(--danger)';
    case 'high-risk':
      return 'var(--warning)';
    case 'exchange':
    case 'vasp':
      return 'var(--accent-cyan)';
    case 'normal':
    default:
      return 'var(--accent-primary)';
  }
};

const getNodeLabel = (nodeId: string, attribution?: any): string => {
  if (attribution?.entity) {
    return attribution.entity;
  }
  return `${nodeId.slice(0, 8)}...${nodeId.slice(-6)}`;
};

export const InvestigationGraph: React.FC<InvestigationGraphProps> = ({
  graph,
  attributions = [],
  risk,
}) => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [showLabels, setShowLabels] = useState(true);

  // Build ReactFlow nodes and edges from graph data
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!graph?.nodes || graph.nodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    const attributionMap = new Map(
      attributions.map((attr) => [attr.wallet, attr])
    );

    // Create nodes
    const nodes: Node[] = graph.nodes.map((nodeData, index) => {
      const attribution = attributionMap.get(nodeData.id);
      const nodeType = nodeData.type || 'unknown';
      const nodeColor = getNodeColor(nodeType);
      const label = getNodeLabel(nodeData.id, attribution);

      return {
        id: nodeData.id,
        data: {
          label: (
            <div className="graph-node">
              {showLabels ? (
                <div className="graph-node__label">{label}</div>
              ) : (
                <div className="graph-node__icon">●</div>
              )}
            </div>
          ),
        },
        position: {
          x: Math.cos((index / graph.nodes.length) * Math.PI * 2) * 300,
          y: Math.sin((index / graph.nodes.length) * Math.PI * 2) * 300,
        },
        style: {
          background: nodeColor,
          border:
            selectedNode === nodeData.id
              ? `3px solid var(--accent-primary)`
              : `2px solid ${nodeColor}`,
          borderRadius: '6px',
          padding: '6px 10px',
          fontSize: '11px',
          color: nodeType === 'vasp' || nodeType === 'exchange' ? '#000' : 'var(--text-primary)',
          fontWeight: 500,
          minWidth: '60px',
          textAlign: 'center',
          cursor: 'pointer',
        },
      };
    });

    // Create edges
    const edges: Edge[] = (graph.edges || []).map((edgeData) => {
      // Filter edges based on selected filter
      if (
        filterType !== 'all' &&
        graph.nodes.find((n) => n.id === edgeData.source)?.type !== filterType &&
        graph.nodes.find((n) => n.id === edgeData.target)?.type !== filterType
      ) {
        return null as any;
      }

      const isSelected =
        selectedNode === edgeData.source || selectedNode === edgeData.target;

      // Scale edge width by value
      let strokeWidth = 1;
      try {
        const valueNum = parseFloat(edgeData.value);
        if (valueNum > 10000) strokeWidth = 3;
        else if (valueNum > 1000) strokeWidth = 2;
      } catch {
        // keep default
      }

      return {
        id: edgeData.id,
        source: edgeData.source,
        target: edgeData.target,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: {
          stroke: isSelected ? 'var(--accent-primary)' : 'var(--border-strong)',
          strokeWidth,
          opacity: isSelected ? 1 : 0.3,
        },
        animated: isSelected,
        label: isSelected ? `${edgeData.value} ${edgeData.token || ''}` : undefined,
      };
    }).filter(Boolean);

    return { nodes, edges };
  }, [graph, attributions, selectedNode, filterType, showLabels]);

  const handleNodeClick = useCallback((nodeId: string) => {
    setSelectedNode(selectedNode === nodeId ? null : nodeId);
  }, [selectedNode]);

  const selectedNodeData = useMemo(() => {
    if (!selectedNode) return null;
    const attribution = attributions.find((a) => a.wallet === selectedNode);
    const nodeInfo = graph?.nodes.find((n) => n.id === selectedNode);
    return { attribution, nodeInfo };
  }, [selectedNode, attributions, graph?.nodes]);

  if (!graph?.nodes || graph.nodes.length === 0) {
    return (
      <div className="investigation-graph">
        <div className="investigation-graph__empty">
          <Network size={48} />
          <h3>No graph data available</h3>
          <p>Blockchain network analysis will appear here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="investigation-graph">
      <div className="investigation-graph__toolbar">
        <div className="investigation-graph__toolbar-group">
          <label className="investigation-graph__filter-label">
            <Filter size={14} />
            Filter by Type:
          </label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="investigation-graph__filter-select"
          >
            <option value="all">All Nodes</option>
            <option value="suspect">Suspect</option>
            <option value="high-risk">High Risk</option>
            <option value="exchange">Exchange</option>
            <option value="vasp">VASP</option>
            <option value="normal">Normal</option>
          </select>
        </div>

        <div className="investigation-graph__toolbar-group">
          <Button
            variant={showLabels ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setShowLabels(!showLabels)}
          >
            {showLabels ? 'Hide' : 'Show'} Labels
          </Button>
        </div>
      </div>

      <Card className="investigation-graph__canvas">
        <ReactFlow
          nodes={flowNodes}
          edges={flowEdges}
          onNodeClick={(event, node) => handleNodeClick(node.id)}
        >
          <Background color="var(--border-subtle)" gap={16} />
          <Controls />
        </ReactFlow>
      </Card>

      {/* Legend */}
      <div className="investigation-graph__legend">
        <div className="investigation-graph__legend-row">
          <div className="investigation-graph__legend-item">
            <div
              className="investigation-graph__legend-node"
              style={{ background: 'var(--danger)' }}
            />
            <span>Suspect</span>
          </div>
          <div className="investigation-graph__legend-item">
            <div
              className="investigation-graph__legend-node"
              style={{ background: 'var(--warning)' }}
            />
            <span>High Risk</span>
          </div>
          <div className="investigation-graph__legend-item">
            <div
              className="investigation-graph__legend-node"
              style={{ background: 'var(--accent-cyan)' }}
            />
            <span>Exchange/VASP</span>
          </div>
          <div className="investigation-graph__legend-item">
            <div
              className="investigation-graph__legend-node"
              style={{ background: 'var(--accent-primary)' }}
            />
            <span>Normal</span>
          </div>
        </div>
      </div>

      {/* Detail drawer */}
      <Drawer
        isOpen={selectedNode !== null}
        onClose={() => setSelectedNode(null)}
        title="Node Details"
      >
        {selectedNodeData && (
          <div className="investigation-graph__detail">
            <div className="investigation-graph__detail-section">
              <h4>Wallet Address</h4>
              <code className="investigation-graph__detail-code">
                {selectedNode}
              </code>
            </div>

            {selectedNodeData.attribution && (
              <>
                <div className="investigation-graph__detail-section">
                  <h4>Attribution</h4>
                  <p className="investigation-graph__detail-entity">
                    {selectedNodeData.attribution.entity}
                  </p>
                  <div className="investigation-graph__detail-meta">
                    <span>Type: {selectedNodeData.attribution.entity_type}</span>
                    <span>
                      Confidence:{' '}
                      {(selectedNodeData.attribution.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </>
            )}

            {selectedNodeData.nodeInfo?.type && (
              <div className="investigation-graph__detail-section">
                <h4>Classification</h4>
                <Badge variant={selectedNodeData.nodeInfo.type === 'suspect' ? 'danger' : 'warning'}>
                  {selectedNodeData.nodeInfo.type.toUpperCase()}
                </Badge>
              </div>
            )}

            <div className="investigation-graph__detail-actions">
              <Button variant="secondary" size="sm">
                View Transactions
              </Button>
              <Button variant="secondary" size="sm">
                View Timeline
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
