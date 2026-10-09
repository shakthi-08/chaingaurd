import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  realtimeUrl,
  type AdvancedIndicators,
  type AIResponse,
  type Attribution,
  type CaseStatus,
  type CaseWallet,
  type EvidenceItem,
  type Graph,
  type HealthStatus,
  type InvestigationAlert,
  type Path,
  type RiskAssessment,
  type Transaction,
} from "./api";
import { Layout } from "./components/Layout";
import { Overview } from "./screens/Overview";
import { NewInvestigation } from "./screens/NewInvestigation";
import { InvestigationWorkspace } from "./components/InvestigationWorkspace";
import "./styles/theme.css";

type RealtimeStatus = "connecting" | "connected" | "disconnected" | "disabled";

const STORAGE_KEY = "chaingaurd.active-investigation";

const emptyRisk = (): RiskAssessment => ({
  overall_score: 0,
  risk_level: "LOW",
  indicators: [],
  findings: [],
  explanations: [],
  evidence_refs: [],
});

const readStoredInvestigation = () => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { caseId: "", walletAddress: "", chain: "ethereum" };
    const parsed = JSON.parse(raw) as {
      caseId?: string;
      walletAddress?: string;
      chain?: string;
    };
    return {
      caseId: typeof parsed.caseId === "string" ? parsed.caseId : "",
      walletAddress:
        typeof parsed.walletAddress === "string" ? parsed.walletAddress : "",
      chain: typeof parsed.chain === "string" ? parsed.chain : "ethereum",
    };
  } catch {
    return { caseId: "", walletAddress: "", chain: "ethereum" };
  }
};

const persistInvestigation = (
  caseId: string,
  walletAddress: string,
  chain: string,
) => {
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ caseId, walletAddress, chain }),
    );
  } catch {
    // Ignore storage failures.
  }
};

const generateCaseId = () =>
  `CASE-${Date.now().toString(36).toUpperCase()}-${Math.random()
    .toString(36)
    .slice(2, 8)
    .toUpperCase()}`;

export function deriveSummary(
  transactions: Transaction[],
  graph: Graph,
  paths: Path[],
  risk: RiskAssessment,
  attributions: Attribution[],
  evidenceCount: number,
) {
  const vaspTypes = new Set(["vasp", "exchange", "custodial_service"]);
  const potentialVASPs = attributions.filter((item) =>
    vaspTypes.has(String(item.entity_type || "").toLowerCase()),
  ).length;
  const suspiciousWallets = new Set<string>();
  for (const indicator of risk.indicators || []) {
    for (const address of indicator.wallet_addresses || []) {
      if (address) suspiciousWallets.add(address.toLowerCase());
    }
  }
  for (const item of attributions) {
    if (item.wallet && item.confidence >= 25) {
      suspiciousWallets.add(item.wallet.toLowerCase());
    }
  }
  return {
    transactions: transactions.length,
    wallets: graph.nodes.length,
    hops: paths.length ? Math.max(...paths.map((path) => path.hop_count)) : 0,
    importantPaths: paths.filter((path) => path.hop_count > 1).length,
    score: risk.overall_score,
    attribution: attributions.length
      ? Math.max(...attributions.map((item) => item.confidence))
      : 0,
    potentialVASPs,
    suspiciousEntities: suspiciousWallets.size,
    evidenceItems: evidenceCount,
  };
}

export default function App() {
  const persistedInvestigation = readStoredInvestigation();
  const [currentScreen, setCurrentScreen] = useState<string>("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeCaseId, setActiveCaseId] = useState<string>(
    persistedInvestigation.caseId,
  );
  const [reportedWallet, setReportedWallet] = useState<string>(
    persistedInvestigation.walletAddress,
  );
  const [chain, setChain] = useState<string>(persistedInvestigation.chain);

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [wallets, setWallets] = useState<CaseWallet[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [graph, setGraph] = useState<Graph>({
    nodes: [],
    edges: [],
    transactions: [],
  });
  const [paths, setPaths] = useState<Path[]>([]);
  const [risk, setRisk] = useState<RiskAssessment>(emptyRisk());
  const [attributions, setAttributions] = useState<Attribution[]>([]);
  const [alerts, setAlerts] = useState<InvestigationAlert[]>([]);
  const [advancedIndicators, setAdvancedIndicators] = useState<AdvancedIndicators>({
    defi: [],
    bridges: [],
    mixers: [],
  });
  const [aiResponse, setAiResponse] = useState<AIResponse | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [caseStatus, setCaseStatus] = useState<CaseStatus | null>(null);

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [realtimeStatus, setRealtimeStatus] =
    useState<RealtimeStatus>("disconnected");
  const analyzedCases = useRef<Set<string>>(new Set());

  const hasActiveCase = Boolean(activeCaseId && reportedWallet);

  const applyReadResults = (
    results: PromiseSettledResult<unknown>[],
  ) => {
    const value = <T,>(index: number, fallback: T): T => {
      const item = results[index];
      return item.status === "fulfilled" ? (item.value as T) : fallback;
    };

    const failures = results
      .map((item, index) =>
        item.status === "rejected"
          ? `${index}:${item.reason instanceof Error ? item.reason.message : "failed"}`
          : null,
      )
      .filter(Boolean);

    setTransactions(value(0, [] as Transaction[]));
    setWallets(value(1, [] as CaseWallet[]));
    const nextGraph = value(2, {
      nodes: [],
      edges: [],
      transactions: [],
    } as Graph);
    setPaths(value(3, [] as Path[]));
    setRisk(value(4, emptyRisk()));
    setAttributions(value(5, [] as Attribution[]));
    setEvidence(value(6, [] as EvidenceItem[]));
    const nextCrossChain = value(7, [] as Graph["cross_chain"]);
    setGraph({ ...nextGraph, cross_chain: nextCrossChain });
    const nextStatus = value(8, null as CaseStatus | null);
    if (nextStatus) setCaseStatus(nextStatus);
    setAlerts(value(9, [] as InvestigationAlert[]));
    setAdvancedIndicators(
      value(10, { defi: [], bridges: [], mixers: [] } as AdvancedIndicators),
    );

    return { failures, status: nextStatus };
  };

  const readPersisted = (caseId: string, walletAddress: string) =>
    Promise.allSettled([
      api.transactions(caseId),
      api.caseWallets(caseId),
      api.graph(caseId),
      walletAddress
        ? api.paths(caseId, walletAddress)
        : Promise.resolve([] as Path[]),
      api.risk(caseId),
      api.attributions(caseId),
      api.evidence(caseId),
      api.crossChain(caseId),
      api.status(caseId),
      api.alerts(caseId),
      api.advancedIndicators(caseId),
    ]);

  const loadData = async (
    caseId: string,
    walletAddress: string,
    forceAnalyze = false,
  ) => {
    if (!caseId) {
      setLoading(false);
      setAnalyzing(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const results = await readPersisted(caseId, walletAddress);
      const { failures, status } = applyReadResults(results);
      setCurrentScreen("workspace");

      if (failures.length === results.length) {
        setError("Unable to load investigation data from the backend.");
      } else if (failures.length) {
        setError(
          `Some investigation views failed to load: ${failures.join("; ")}`,
        );
      }

      // Show workspace with persisted reads before any analyze write.
      setLoading(false);

      const statusValue = String(status?.status || "").toUpperCase();
      const shouldAnalyze =
        forceAnalyze ||
        (statusValue !== "COMPLETED" && !analyzedCases.current.has(caseId));

      if (shouldAnalyze) {
        setAnalyzing(true);
        analyzedCases.current.add(caseId);
        try {
          await api.analyze(caseId);
          const refreshed = await readPersisted(caseId, walletAddress);
          const refreshOutcome = applyReadResults(refreshed);
          if (refreshOutcome.failures.length === refreshed.length) {
            setError("Unable to load investigation data from the backend.");
          } else if (refreshOutcome.failures.length) {
            setError(
              `Some investigation views failed to load: ${refreshOutcome.failures.join("; ")}`,
            );
          }
        } catch (reason) {
          setError(
            reason instanceof Error
              ? `Analysis failed: ${reason.message}`
              : "Analysis failed for this case.",
          );
        } finally {
          setAnalyzing(false);
        }
      }
    } catch (reason) {
      setError(
        reason instanceof Error
          ? `Unable to load investigation data: ${reason.message}`
          : "Unable to load investigation data from the backend yet.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() =>
        setHealth({
          status: "error",
          real_mode: false,
          demo_mode: false,
        }),
      );
  }, []);

  useEffect(() => {
    if (!activeCaseId || !reportedWallet) {
      return;
    }
    void loadData(activeCaseId, reportedWallet);
  }, [activeCaseId, reportedWallet]);

  useEffect(() => {
    persistInvestigation(activeCaseId, reportedWallet, chain);
  }, [activeCaseId, reportedWallet, chain]);

  useEffect(() => {
    if (!activeCaseId) {
      setRealtimeStatus("disconnected");
      return;
    }
    if (health?.real_mode) {
      setRealtimeStatus("disabled");
      return;
    }
    const url = realtimeUrl(activeCaseId);
    if (!url) {
      setRealtimeStatus("disabled");
      return;
    }

    const socket = new WebSocket(url);
    setRealtimeStatus("connecting");
    socket.onopen = () => setRealtimeStatus("connected");
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as {
        error?: string;
        event_type?: string;
        payload?: Omit<Transaction, "tx_hash" | "from" | "to" | "timestamp"> & {
          from: string;
          to: string;
        };
        transaction_ref?: string;
        timestamp: string;
      };
      if (event.error) {
        setRealtimeStatus("disabled");
        socket.close();
        return;
      }
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
        .graph(activeCaseId)
        .then((nextGraph) =>
          setGraph((current) => ({
            ...nextGraph,
            cross_chain: current.cross_chain || [],
          })),
        )
        .catch(() => undefined);
    };
    socket.onclose = () =>
      setRealtimeStatus((current) =>
        current === "disabled" ? current : "disconnected",
      );
    socket.onerror = () => setRealtimeStatus("disconnected");
    return () => socket.close();
  }, [activeCaseId, health?.real_mode]);

  const summary = useMemo(
    () =>
      deriveSummary(
        transactions,
        graph,
        paths,
        risk,
        attributions,
        evidence.length,
      ),
    [transactions, graph, paths, risk, attributions, evidence.length],
  );

  const handleNavChange = (navId: string) => {
    if (navId === "investigations") {
      setCurrentScreen(hasActiveCase ? "workspace" : "overview");
      return;
    }
    if (navId === "status") {
      void api.health().then(setHealth).catch(() => undefined);
      setCurrentScreen("status");
      return;
    }
    setCurrentScreen(navId);
  };

  const handleStartInvestigation = async (
    walletAddress: string,
    selectedChain = "ethereum",
    maxHops = 1,
  ) => {
    const trimmed = walletAddress.trim();
    if (!trimmed) {
      setError("Wallet address is required");
      return;
    }

    const caseId = generateCaseId();
    setError(null);
    setLoading(true);

    try {
      const ingest = await api.wallets(caseId, trimmed, selectedChain, maxHops);
      const notices: string[] = [];
      if (ingest.provider_empty) {
        notices.push(
          "Provider returned no transactions for this wallet (provider_empty).",
        );
      }
      if (ingest.truncated) {
        notices.push("Ingestion was truncated before all hops completed.");
      }
      if (ingest.hop_errors?.length) {
        notices.push(
          `Hop errors: ${ingest.hop_errors
            .map((item) => `${item.wallet}@${item.hop}: ${item.error}`)
            .join("; ")}`,
        );
      }
      if (notices.length) {
        setError(notices.join(" "));
      }
      // Analyze runs once via loadData after case is set — not in parallel with ingest.
      setActiveCaseId(caseId);
      setReportedWallet(trimmed.toLowerCase());
      setChain(selectedChain);
      setCurrentScreen("workspace");
    } catch (reason) {
      setError(
        reason instanceof Error
          ? `Unable to start investigation: ${reason.message}`
          : "Unable to start investigation with the backend.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (activeCaseId && reportedWallet) {
      analyzedCases.current.delete(activeCaseId);
      void loadData(activeCaseId, reportedWallet, true);
    }
  };

  const handleAskAi = async (question: string) => {
    if (!activeCaseId) return null;
    const response = await api.ai.ask(activeCaseId, question);
    setAiResponse(response);
    return response;
  };

  const handleAiAction = async (
    action: "summary" | "risk" | "attribution" | "path" | "nextSteps",
  ) => {
    if (!activeCaseId) return null;
    const runners = {
      summary: () => api.ai.summary(activeCaseId),
      risk: () => api.ai.risk(activeCaseId),
      attribution: () => api.ai.attribution(activeCaseId, reportedWallet),
      path: () => api.ai.path(activeCaseId, paths[0]?.rank),
      nextSteps: () => api.ai.nextSteps(activeCaseId),
    };
    const response = await runners[action]();
    setAiResponse(response);
    return response;
  };

  const handleExportReport = async () => {
    if (!activeCaseId) return;
    await api.downloadReport(activeCaseId);
  };

  const workspaceData = {
    summary,
    transactions,
    graph,
    paths,
    risk,
    attributions,
    evidence,
    wallets,
    alerts,
    advancedIndicators,
    aiResponse,
    health,
    chain,
    caseStatus: caseStatus ?? undefined,
    analyzing,
    loading: loading || analyzing,
    error,
  };

  const renderContent = () => {
    if (error && currentScreen !== "new-investigation") {
      // keep showing the screen with the banner below via workspace/overview
    }

    switch (currentScreen) {
      case "overview":
        return (
          <Overview
            hasActiveCase={hasActiveCase}
            onStartInvestigation={() => setCurrentScreen("new-investigation")}
            onOpenWorkspace={() => setCurrentScreen("workspace")}
            onNavigate={handleNavChange}
            summary={summary}
            risk={risk}
            recentTransactions={transactions.slice(0, 5)}
            aiSummary={aiResponse?.answer}
            error={error}
            health={health}
            evidenceCount={evidence.length}
            caseStatus={caseStatus ?? undefined}
          />
        );

      case "new-investigation":
        return (
          <NewInvestigation
            onSubmit={handleStartInvestigation}
            isLoading={loading}
            error={error}
            realMode={Boolean(health?.real_mode)}
          />
        );

      case "status":
        return (
          <Overview
            hasActiveCase={hasActiveCase}
            onStartInvestigation={() => setCurrentScreen("new-investigation")}
            onOpenWorkspace={() => setCurrentScreen("workspace")}
            onNavigate={handleNavChange}
            summary={summary}
            risk={risk}
            recentTransactions={transactions.slice(0, 5)}
            aiSummary={
              health
                ? `Backend ${health.status}. Provider: ${health.blockchain_provider || "unknown"}. Mode: ${health.real_mode ? "REAL" : health.demo_mode ? "DEMO" : "configured"}.`
                : "Checking backend health..."
            }
            error={error}
            health={health}
            evidenceCount={evidence.length}
            caseStatus={caseStatus ?? undefined}
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
      case "evidence":
        return (
          <InvestigationWorkspace
            caseId={activeCaseId}
            walletAddress={reportedWallet}
            data={workspaceData}
            initialTab={
              currentScreen === "workspace" ? "overview" : currentScreen
            }
            onNavigate={handleNavChange}
            onRefresh={handleRefresh}
            onAskAi={handleAskAi}
            onAiAction={handleAiAction}
            onExportReport={handleExportReport}
          />
        );

      default:
        return (
          <Overview
            hasActiveCase={hasActiveCase}
            onStartInvestigation={() => setCurrentScreen("new-investigation")}
            onOpenWorkspace={() => setCurrentScreen("workspace")}
            onNavigate={handleNavChange}
            summary={summary}
            risk={risk}
            recentTransactions={transactions.slice(0, 5)}
            aiSummary={aiResponse?.answer}
            error={error}
            health={health}
            evidenceCount={evidence.length}
            caseStatus={caseStatus ?? undefined}
          />
        );
    }
  };

  return (
    <Layout
      activeNav={currentScreen === "status" ? "status" : currentScreen}
      onNavChange={handleNavChange}
      sidebarCollapsed={sidebarCollapsed}
      onToggleSidebar={() => setSidebarCollapsed(!sidebarCollapsed)}
      caseId={activeCaseId || undefined}
      walletAddress={reportedWallet || undefined}
      riskScore={risk.overall_score || undefined}
      hasActiveCase={hasActiveCase}
      realtimeStatus={realtimeStatus}
      onRefresh={hasActiveCase ? handleRefresh : undefined}
      loading={loading || analyzing}
      error={error}
    >
      {renderContent()}
    </Layout>
  );
}
