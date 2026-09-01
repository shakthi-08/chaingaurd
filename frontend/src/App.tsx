import React, { useEffect, useMemo, useState } from "react";
import {
  api,
  realtimeUrl,
  type AIResponse,
  type Attribution,
  type Graph,
  type Path,
  type RiskAssessment,
  type Transaction,
} from "./api";
import { Layout } from "./components/Layout";
import { Overview } from "./screens/Overview";
import { NewInvestigation } from "./screens/NewInvestigation";
import { InvestigationWorkspace } from "./components/InvestigationWorkspace";
import "./styles/theme.css";

type RealtimeStatus = "connecting" | "connected" | "disconnected";

const CASE_ID = import.meta.env.VITE_CASE_ID ?? "";
const REPORTED_WALLET = import.meta.env.VITE_WALLET_ADDRESS ?? "";

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

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<string>("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Data state
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
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null);

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [realtimeStatus, setRealtimeStatus] =
    useState<RealtimeStatus>("connecting");

  const hasActiveCase = Boolean(
    CASE_ID && (transactions.length || risk.indicators.length || attributions.length || !!aiResponse),
  );

  const loadData = async () => {
    if (!CASE_ID) {
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [txs, nextGraph, nextPaths, nextAttributions, nextRisk] =
        await Promise.all([
          api.transactions(CASE_ID),
          api.graph(CASE_ID),
          api.paths(CASE_ID, REPORTED_WALLET || ""),
          api.attributions(CASE_ID),
          api.risk(CASE_ID),
        ]);
      setTransactions(txs);
      setGraph(nextGraph);
      setPaths(nextPaths);
      setAttributions(nextAttributions);
      setRisk(nextRisk);
      setAiResponse(null);
    } catch (reason) {
      setTransactions([]);
      setGraph({ nodes: [], edges: [], transactions: [] });
      setPaths([]);
      setAttributions([]);
      setRisk({
        overall_score: 0,
        risk_level: "LOW",
        indicators: [],
        findings: [],
        explanations: [],
        evidence_refs: [],
      });
      setAiResponse(null);
      setError(
        reason instanceof Error
          ? `Unable to load investigation data: ${reason.message}`
          : "Unable to load investigation data from the backend yet.",
      );
    } finally {
      setLoading(false);
    }
  };

  // Load data on mount
  useEffect(() => {
    void loadData();
  }, []);

  // Real-time WebSocket connection
  useEffect(() => {
    if (!CASE_ID) {
      setRealtimeStatus("disconnected");
      return;
    }

    const socket = new WebSocket(realtimeUrl(CASE_ID));
    socket.onopen = () => setRealtimeStatus("connected");
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as {
        event_type: string;
        payload?: Omit<
          Transaction,
          "tx_hash" | "from" | "to" | "timestamp"
        > & {
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
          : [...current, transaction]
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
    [transactions, graph, paths, risk, attributions]
  );

  const handleNavChange = (navId: string) => {
    setCurrentScreen(navId);
  };

  const handleStartInvestigation = (walletAddress: string) => {
    // In a real app, this would navigate to a new case
    // For now, we'll just switch to workspace view
    setCurrentScreen("workspace");
  };

  // Render content based on current screen
  const renderContent = () => {
    switch (currentScreen) {
      case "overview":
        return (
          <Overview
            hasActiveCase={hasActiveCase}
            onStartInvestigation={() => setCurrentScreen("new-investigation")}
            summary={summary}
            risk={risk}
            recentTransactions={transactions.slice(0, 5)}
            aiSummary={aiResponse?.answer}
          />
        );

      case "new-investigation":
        return (
          <NewInvestigation
            onSubmit={handleStartInvestigation}
            isLoading={loading}
          />
        );

      case "workspace":
      case "transactions":
      case "fund-flow":
      case "graph":
      case "risk":
      case "attribution":
      case "ai":
      case "timeline":
      case "report":
        return (
          <InvestigationWorkspace
            caseId={CASE_ID}
            walletAddress={REPORTED_WALLET}
            data={{
              summary,
              transactions,
              graph,
              paths,
              risk,
              attributions,
              aiResponse,
            }}
            initialTab={currentScreen === 'workspace' ? 'overview' : currentScreen}
            onNavigate={handleNavChange}
          />
        );

      default:
        return (
          <Overview
            hasActiveCase={hasActiveCase}
            onStartInvestigation={() => setCurrentScreen("new-investigation")}
            summary={summary}
            risk={risk}
            recentTransactions={transactions.slice(0, 5)}
            aiSummary={aiResponse?.answer}
          />
        );
    }
  };

  return (
    <Layout
      activeNav={currentScreen}
      onNavChange={handleNavChange}
      sidebarCollapsed={sidebarCollapsed}
      onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
      caseId={CASE_ID || undefined}
      walletAddress={REPORTED_WALLET || undefined}
      riskScore={risk.overall_score || undefined}
      hasActiveCase={hasActiveCase}
      realtimeStatus={realtimeStatus}
    >
      {renderContent()}
    </Layout>
  );
}
