import React, { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
  MarkerType,
} from "reactflow";
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Database,
  Eye,
  FileSearch,
  Filter,
  GitBranch,
  RefreshCw,
  Search,
  ShieldAlert,
  Target,
  WalletCards,
  X,
} from "lucide-react";
import {
  api,
  realtimeUrl,
  type AIResponse,
  type Attribution,
  type CrossChainMovement,
  type Graph,
  type Path,
  type RiskAssessment,
  type Transaction,
} from "./api";

const CASE_ID = "CASE-DEMO-001";
const REPORTED_WALLET = "0x1111111111111111111111111111111111111111";
type RealtimeStatus = "connecting" | "connected" | "disconnected";

export function deriveSummary(
  transactions: Transaction[],
  graph: Graph,
  paths: Path[],
  risk: RiskAssessment,
  attributions: Attribution[],
) {
  return {
    transactions: transactions.length,
    wallets: graph.nodes.length,
    hops: paths.length ? Math.max(...paths.map((path) => path.hop_count)) : 0,
    importantPaths: paths.filter((path) => path.hop_count > 1).length,
    score: risk.overall_score,
    attribution: attributions.length
      ? Math.max(...attributions.map((item) => item.confidence))
      : 0,
  };
}

function short(value: string) {
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}
function date(value: string) {
  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
function amount(value: string) {
  return Number(value).toLocaleString();
}

export default function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [graph, setGraph] = useState<Graph>({
    nodes: [],
    edges: [],
    transactions: [],
  });
  const [paths, setPaths] = useState<Path[]>([]);
  const [risk, setRisk] = useState<RiskAssessment>({
    overall_score: 0,
    risk_level: "LOW",
    indicators: [],
    findings: [],
    explanations: [],
    evidence_refs: [],
  });
  const [attributions, setAttributions] = useState<Attribution[]>([]);
  const [crossChain, setCrossChain] = useState<CrossChainMovement[]>([]);
  const [selectedCrossChain, setSelectedCrossChain] =
    useState<CrossChainMovement | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<Path | null>(null);
  const [timelineFilter, setTimelineFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [realtimeStatus, setRealtimeStatus] =
    useState<RealtimeStatus>("connecting");

  const loadData = async (reanalyze = false) => {
    setLoading(true);
    setError(null);
    try {
      const [
        txs,
        nextGraph,
        nextPaths,
        nextAttributions,
        nextRisk,
        nextCrossChain,
      ] = await Promise.all([
        api.transactions(CASE_ID),
        api.graph(CASE_ID),
        api.paths(CASE_ID, REPORTED_WALLET),
        api.attributions(CASE_ID),
        reanalyze ? api.analyze(CASE_ID) : api.risk(CASE_ID),
        api.crossChain(CASE_ID),
      ]);
      setTransactions(txs);
      setGraph(nextGraph);
      setPaths(nextPaths);
      setAttributions(nextAttributions);
      setRisk(nextRisk);
      setCrossChain(nextCrossChain);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Backend unavailable",
      );
    } finally {
      setLoading(false);
      setBusy(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  useEffect(() => {
    const socket = new WebSocket(realtimeUrl(CASE_ID));
    socket.onopen = () => setRealtimeStatus("connected");
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as {
        event_type: string;
        payload?: Omit<Transaction, "tx_hash" | "from" | "to" | "timestamp"> & {
          from: string;
          to: string;
        };
        transaction_ref?: string;
        timestamp: string;
      };
      if (
        event.event_type !== "new_transaction" ||
        !event.payload ||
        !event.transaction_ref
      )
        return;
      const transaction: Transaction = {
        tx_hash: event.transaction_ref,
        from: event.payload.from,
        to: event.payload.to,
        value: event.payload.value,
        token: event.payload.token,
        timestamp: event.timestamp,
        block: event.payload.block,
      };
      setTransactions((current) =>
        current.some((item) => item.tx_hash === transaction.tx_hash)
          ? current
          : [...current, transaction],
      );
      void api
        .graph(CASE_ID)
        .then(setGraph)
        .catch(() => undefined);
    };
    socket.onclose = () => setRealtimeStatus("disconnected");
    socket.onerror = () => setRealtimeStatus("disconnected");
    return () => socket.close();
  }, []);

  const summary = useMemo(
    () => deriveSummary(transactions, graph, paths, risk, attributions),
    [transactions, graph, paths, risk, attributions],
  );
  const filteredTransactions = useMemo(
    () =>
      transactions.filter((tx) =>
        `${tx.tx_hash} ${tx.from} ${tx.to} ${tx.token}`
          .toLowerCase()
          .includes(timelineFilter.toLowerCase()),
      ),
    [transactions, timelineFilter],
  );
  const nodes: Node[] = useMemo(
    () =>
      graph.nodes.map((node, index) => ({
        id: node.id,
        position: {
          x: (index % 4) * 210 + 50,
          y: Math.floor(index / 4) * 125 + 50,
        },
        data: { label: short(node.id) },
        className: selectedNode === node.id ? "selected-flow-node" : "",
      })),
    [graph.nodes, selectedNode],
  );
  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: `${amount(edge.value)} ${edge.token ?? ""}`,
        animated: Boolean(
          selectedPath?.transactions.includes(edge.tx_ref) ||
          (selectedCrossChain &&
            [
              selectedCrossChain.source_transaction,
              selectedCrossChain.destination_transaction,
            ].includes(edge.tx_ref)),
        ),
        markerEnd: { type: MarkerType.ArrowClosed },
        style: {
          stroke: selectedPath?.transactions.includes(edge.tx_ref)
            ? selectedCrossChain?.source_transaction === edge.tx_ref ||
              selectedCrossChain?.destination_transaction === edge.tx_ref
              ? "#49748a"
              : "#e2744e"
            : "#6d8a96",
          strokeWidth: selectedPath?.transactions.includes(edge.tx_ref)
            ? 3
            : 1.5,
        },
      })),
    [graph.edges, selectedPath, selectedCrossChain],
  );
  const selectedNodeTransactions = selectedNode
    ? transactions.filter(
        (tx) => tx.from === selectedNode || tx.to === selectedNode,
      )
    : [];
  const selectedAttribution = selectedNode
    ? attributions.filter((item) => item.wallet === selectedNode)
    : [];
  const intermediaries = [
    ...new Set(paths.flatMap((path) => path.wallets.slice(1, -1))),
  ].slice(0, 8);

  const analyze = () => {
    setBusy(true);
    void loadData(true);
  };

  const askAssistant = async (action: () => Promise<AIResponse>) => {
    setAiBusy(true);
    try {
      setAiResponse(await action());
    } catch (reason) {
      setAiResponse({
        answer:
          reason instanceof Error ? reason.message : "AI assistance failed.",
        evidence_refs: [],
        provider: "error",
        model: null,
        ai_assisted: false,
        provider_status: "error",
        limitations: ["The assistant could not complete this request."],
      });
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldAlert size={22} />
          </div>
          <div>
            <strong>ChainGuard</strong>
            <span>Investigator console</span>
          </div>
        </div>
        <div className="case-switcher">
          <span className="eyebrow">ACTIVE CASE</span>
          <strong>{CASE_ID}</strong>
          <span className="case-status">
            <i /> Open investigation
          </span>
        </div>
        <nav>
          <a className="active">
            <Target size={16} /> Case overview
          </a>
          <a href="#fund-flow">
            <GitBranch size={16} /> Fund flow
          </a>
          <a href="#timeline">
            <Activity size={16} /> Timeline
          </a>
          <a href="#evidence">
            <FileSearch size={16} /> Evidence
          </a>
        </nav>
        <div className="sidebar-footer">
          <span className="demo-dot" /> DEMO / SYNTHETIC DATA
          <div className="system-state">
            <span className="pulse" /> API connected
          </div>
        </div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Cases / Active investigation</span>
            <h1>Transaction intelligence</h1>
          </div>
          <div className={`realtime-status ${realtimeStatus}`}>
            <i /> {realtimeStatus}
          </div>
          <div className="top-actions">
            <button
              className="button secondary"
              onClick={() => {
                setBusy(true);
                void loadData();
              }}
              disabled={busy}
            >
              <RefreshCw size={15} /> Refresh data
            </button>
            <button
              className="button primary"
              onClick={analyze}
              disabled={busy}
            >
              <Search size={15} /> Analyze case
            </button>
          </div>
        </header>
        {error && (
          <div className="error-banner">
            <AlertTriangle size={18} />
            <div>
              <strong>Backend unavailable</strong>
              <span>
                {error}. Start FastAPI to load this investigation. No fallback
                data is being shown.
              </span>
            </div>
            <button onClick={() => setError(null)}>
              <X size={16} />
            </button>
          </div>
        )}
        {loading ? (
          <div className="loading-state">
            <div className="spinner" />
            <strong>Loading investigation evidence...</strong>
            <span>
              Querying transactions, graph, risk, and attribution services.
            </span>
          </div>
        ) : (
          <>
            <section className="case-header">
              <div>
                <div className="tag-row">
                  <span className="tag orange">DEMO CASE</span>
                  <span className="tag green">OPEN</span>
                </div>
                <h2>{CASE_ID}</h2>
                <p>
                  Reported wallet investigation across Ethereum transaction
                  activity.
                </p>
              </div>
              <div className="case-meta">
                <div>
                  <span>Complaint reference</span>
                  <strong>CYBER-001-demo</strong>
                </div>
                <div>
                  <span>Reported wallet</span>
                  <strong className="mono">{short(REPORTED_WALLET)}</strong>
                </div>
                <div>
                  <span>Created</span>
                  <strong>01 Jan 2024</strong>
                </div>
              </div>
            </section>
            <section className="summary-grid">
              <Metric
                icon={<Database />}
                label="Transactions analyzed"
                value={summary.transactions}
              />
              <Metric
                icon={<WalletCards />}
                label="Wallets discovered"
                value={summary.wallets}
              />
              <Metric
                icon={<GitBranch />}
                label="Deepest hop"
                value={`${summary.hops} hops`}
              />
              <Metric
                icon={<Eye />}
                label="Important paths"
                value={summary.importantPaths}
              />
              <Metric
                icon={<ShieldAlert />}
                label="Risk score"
                value={`${summary.score}/100`}
                accent={risk.risk_level.toLowerCase()}
              />
              <Metric
                icon={<Target />}
                label="Attribution confidence"
                value={`${summary.attribution.toFixed(1)}%`}
              />
            </section>
            <div className="dashboard-grid">
              <section className="panel risk-panel">
                <PanelHeading
                  icon={<ShieldAlert />}
                  title="Risk assessment"
                  action={
                    <span
                      className={`risk-badge ${risk.risk_level.toLowerCase()}`}
                    >
                      {risk.risk_level} · {risk.overall_score}
                    </span>
                  }
                />
                <p className="panel-note">
                  Deterministic investigative indicators. A high score does not
                  prove criminal activity.
                </p>
                {risk.indicators.length === 0 ? (
                  <Empty text="No suspicious patterns detected." />
                ) : (
                  <div className="indicator-list">
                    {risk.indicators.map((item) => (
                      <div
                        className="indicator"
                        key={`${item.type}-${item.transaction_refs.join("-")}`}
                      >
                        <div className="indicator-top">
                          <strong>{item.type.replaceAll("_", " ")}</strong>
                          <span>{item.score} pts</span>
                        </div>
                        <div className="severity">
                          <i /> {item.severity} severity ·{" "}
                          {Math.round(item.confidence * 100)}% confidence
                        </div>
                        <p>{item.explanation}</p>
                        <small>Evidence: {item.evidence_refs.join(", ")}</small>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section className="panel case-info">
                <PanelHeading
                  icon={<FileSearch />}
                  title="Case record"
                  action={
                    <span className="record-state">● Evidence linked</span>
                  }
                />
                <div className="record-list">
                  <Record label="Status" value="Open investigation" />
                  <Record label="Blockchain" value="Ethereum" />
                  <Record label="Data source" value="Synthetic demo provider" />
                  <Record
                    label="Reported wallet"
                    value={short(REPORTED_WALLET)}
                    mono
                  />
                  <Record
                    label="Caveat"
                    value="Attributions are leads, not proof."
                  />
                </div>
              </section>
              <section className="panel graph-panel" id="fund-flow">
                <PanelHeading
                  icon={<GitBranch />}
                  title="Fund-flow graph"
                  action={
                    <span className="panel-hint">
                      {graph.nodes.length} nodes · {graph.edges.length} edges
                    </span>
                  }
                />
                <div className="graph-toolbar">
                  <span>
                    <i className="legend-dot source" /> Wallet node
                  </span>
                  <span>
                    <i className="legend-line" /> Transaction direction
                  </span>
                  {selectedPath && (
                    <button
                      className="clear-path"
                      onClick={() => setSelectedPath(null)}
                    >
                      Clear path highlight
                    </button>
                  )}
                </div>
                <div className="flow-wrap">
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    fitView
                    onNodeClick={(_, node) => setSelectedNode(node.id)}
                    onPaneClick={() => setSelectedNode(null)}
                  >
                    <Background color="#d5e0e2" gap={22} />
                    <Controls />
                    <MiniMap nodeColor="#e2744e" />
                  </ReactFlow>
                </div>
              </section>
              <section className="panel node-panel">
                <PanelHeading
                  icon={<WalletCards />}
                  title="Selected wallet"
                  action={
                    selectedNode ? (
                      <span className="mono">{short(selectedNode)}</span>
                    ) : null
                  }
                />
                {selectedNode ? (
                  <>
                    <div className="selected-address mono">{selectedNode}</div>
                    <div className="node-stats">
                      <Record label="Chain" value="Ethereum" />
                      <Record
                        label="Transactions"
                        value={selectedNodeTransactions.length}
                      />
                      <Record label="Labels" value="synthetic-demo" />
                    </div>
                    {selectedAttribution.length > 0 && (
                      <div className="mini-attribution">
                        <span>Likely associated</span>
                        <strong>{selectedAttribution[0].entity}</strong>
                        <em>{selectedAttribution[0].confidence}% confidence</em>
                      </div>
                    )}
                  </>
                ) : (
                  <Empty text="Select a wallet node to inspect its activity." />
                )}
              </section>
              <section className="panel paths-panel">
                <PanelHeading
                  icon={<ArrowUpRight />}
                  title="Ranked paths"
                  action={
                    <span className="panel-hint">
                      Backend-ranked · max 4 hops
                    </span>
                  }
                />
                {paths.length === 0 ? (
                  <Empty text="No paths returned for the reported wallet." />
                ) : (
                  <div className="path-list">
                    {paths.slice(0, 6).map((path) => (
                      <button
                        className={`path-row ${selectedPath?.rank === path.rank ? "selected" : ""}`}
                        key={path.rank}
                        onClick={() => setSelectedPath(path)}
                      >
                        <span className="rank">0{path.rank}</span>
                        <div>
                          <strong>
                            {short(path.start_wallet)} <span>→</span>{" "}
                            {short(path.end_wallet)}
                          </strong>
                          <small>{path.wallets.map(short).join(" → ")}</small>
                        </div>
                        <div className="path-value">
                          <strong>{amount(path.total_value)}</strong>
                          <small>{path.hop_count} hops</small>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </section>
              <section className="panel attribution-panel">
                <PanelHeading
                  icon={<Target />}
                  title="Entity / VASP leads"
                  action={<span className="tag blue">HYPOTHESES</span>}
                />
                {attributions.length === 0 ? (
                  <Empty text="No seeded entity matches for this case." />
                ) : (
                  <div className="attribution-list">
                    {attributions.map((item) => (
                      <div
                        className="attribution"
                        key={`${item.wallet}-${item.entity_id}`}
                      >
                        <div className="entity-avatar">
                          {item.entity.slice(5, 6)}
                        </div>
                        <div>
                          <strong>Likely associated with {item.entity}</strong>
                          <small>
                            {short(item.wallet)} · {item.entity_type} ·{" "}
                            {item.confidence}% confidence
                          </small>
                          <p>{item.reasons.join(" · ")}</p>
                          <em>{item.source}</em>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section className="panel timeline-panel" id="timeline">
                <PanelHeading
                  icon={<Activity />}
                  title="Transaction timeline"
                  action={
                    <label className="search-input">
                      <Filter size={14} />
                      <input
                        value={timelineFilter}
                        onChange={(event) =>
                          setTimelineFilter(event.target.value)
                        }
                        placeholder="Filter hash, wallet, token"
                      />
                    </label>
                  }
                />
                {filteredTransactions.length === 0 ? (
                  <Empty text="No transactions match this filter." />
                ) : (
                  <div className="timeline">
                    {filteredTransactions.map((tx) => (
                      <div className="timeline-row" key={tx.tx_hash}>
                        <div className="timeline-marker" />
                        <div className="timeline-date">
                          {date(tx.timestamp)}
                        </div>
                        <div className="timeline-detail">
                          <strong className="mono">{tx.tx_hash}</strong>
                          <span>
                            <b>{short(tx.from)}</b> → <b>{short(tx.to)}</b>
                          </span>
                        </div>
                        <div className="timeline-amount">
                          <strong>{amount(tx.value)}</strong>
                          <span>
                            {tx.token ?? "native"} · block {tx.block ?? "—"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section className="panel intermediary-panel">
                <PanelHeading
                  icon={<GitBranch />}
                  title="Intermediary wallets"
                  action={
                    <span className="panel-hint">
                      Derived from traced paths
                    </span>
                  }
                />
                {intermediaries.length === 0 ? (
                  <Empty text="No intermediary wallets identified." />
                ) : (
                  <div className="intermediary-list">
                    {intermediaries.map((wallet) => (
                      <div key={wallet}>
                        <span className="intermediary-index">
                          {intermediaries.indexOf(wallet) + 1}
                        </span>
                        <span className="mono">{short(wallet)}</span>
                        <small>Observed path intermediary</small>
                        <ArrowUpRight size={15} />
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section className="panel evidence-panel" id="evidence">
                <PanelHeading
                  icon={<FileSearch />}
                  title="Evidence register"
                  action={
                    <span className="panel-hint">
                      {risk.evidence_refs.length} references
                    </span>
                  }
                />
                {risk.evidence_refs.length === 0 ? (
                  <Empty text="Evidence references will appear after analysis." />
                ) : (
                  <div className="evidence-list">
                    {risk.evidence_refs.slice(0, 12).map((ref) => (
                      <div key={ref}>
                        <span className="evidence-type">TX</span>
                        <div>
                          <strong className="mono">{ref}</strong>
                          <small>
                            Source: deterministic analysis · linked transaction
                            evidence
                          </small>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              <section className="panel assistant-panel">
                <PanelHeading
                  icon={<Search />}
                  title="Investigator assistant"
                  action={<span className="tag blue">READ-ONLY</span>}
                />
                <p className="panel-note">
                  AI explanations use only verified ChainGuard context. They
                  never change investigation data.
                </p>
                <div className="assistant-actions">
                  <button
                    onClick={() =>
                      void askAssistant(() => api.ai.summary(CASE_ID))
                    }
                    disabled={aiBusy}
                  >
                    Summarize case
                  </button>
                  <button
                    onClick={() =>
                      void askAssistant(() =>
                        api.ai.path(CASE_ID, selectedPath?.rank),
                      )
                    }
                    disabled={aiBusy}
                  >
                    Explain fund flow
                  </button>
                  <button
                    onClick={() =>
                      void askAssistant(() => api.ai.risk(CASE_ID))
                    }
                    disabled={aiBusy}
                  >
                    Explain risk
                  </button>
                  <button
                    onClick={() =>
                      void askAssistant(() =>
                        api.ai.attribution(CASE_ID, selectedNode ?? undefined),
                      )
                    }
                    disabled={aiBusy}
                  >
                    Explain attribution
                  </button>
                  <button
                    onClick={() =>
                      void askAssistant(() => api.ai.nextSteps(CASE_ID))
                    }
                    disabled={aiBusy}
                  >
                    Suggest next steps
                  </button>
                </div>
                {aiBusy && (
                  <div className="assistant-loading">
                    Requesting grounded explanation...
                  </div>
                )}
                {aiResponse && (
                  <div
                    className={`assistant-response ${aiResponse.provider_status}`}
                  >
                    <div className="assistant-response-top">
                      <strong>
                        {aiResponse.ai_assisted
                          ? `${aiResponse.provider} assistant`
                          : "AI assistance unavailable"}
                      </strong>
                      <span>
                        {aiResponse.model ?? "No configured provider"}
                      </span>
                    </div>
                    <p>{aiResponse.answer}</p>
                    {aiResponse.evidence_refs.length > 0 && (
                      <small>
                        References: {aiResponse.evidence_refs.join(", ")}
                      </small>
                    )}
                    <ul>
                      {aiResponse.limitations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
              <section className="panel cross-chain-panel">
                <PanelHeading
                  icon={<GitBranch />}
                  title="Cross-chain correlations"
                  action={<span className="tag blue">DEMO / SAMPLE</span>}
                />
                {crossChain.length === 0 ? (
                  <Empty text="No synthetic cross-chain movements correlated." />
                ) : (
                  <div className="cross-chain-list">
                    {crossChain.map((movement) => (
                      <button
                        className={`cross-chain-row ${selectedCrossChain?.source_transaction === movement.source_transaction ? "selected" : ""}`}
                        key={`${movement.source_transaction}-${movement.destination_transaction}`}
                        onClick={() => setSelectedCrossChain(movement)}
                      >
                        <div className="cross-chain-route">
                          <strong>{movement.source_chain}</strong>
                          <span>→</span>
                          <strong>{movement.destination_chain}</strong>
                        </div>
                        <div>
                          <strong className="mono">
                            {short(movement.source_transaction)} →{" "}
                            {short(movement.destination_transaction)}
                          </strong>
                          <small>
                            {movement.bridge_service} · {movement.confidence}%
                            correlation confidence
                          </small>
                          <p>{movement.reasons.join(" · ")}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </section>
              <footer className="disclaimer">
                <AlertTriangle size={15} />
                <span>
                  ChainGuard provides investigative leads and evidence
                  organization. Attribution and risk indicators require human
                  review and do not establish ownership or criminality.
                </span>
                <button
                  className="button secondary"
                  onClick={() =>
                    alert(
                      "Report generation is not available because no backend report endpoint exists.",
                    )
                  }
                >
                  Generate report
                </button>
              </footer>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className={`metric ${accent ?? ""}`}>
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
function PanelHeading({
  icon,
  title,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="panel-heading">
      <div>
        <span className="panel-icon">{icon}</span>
        <h3>{title}</h3>
      </div>
      {action}
    </div>
  );
}
function Record({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | number;
  mono?: boolean;
}) {
  return (
    <div className="record">
      <span>{label}</span>
      <strong className={mono ? "mono" : ""}>{value}</strong>
    </div>
  );
}
function Empty({ text }: { text: string }) {
  return (
    <div className="empty">
      <span>{text}</span>
    </div>
  );
}
