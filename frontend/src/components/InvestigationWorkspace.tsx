import React, { useEffect, useState } from "react";
import { CaseSummary } from "./Layout";
import { Overview } from "../screens/Overview";
import { Transactions } from "../screens/Transactions";
import { RiskAndFraud } from "../screens/RiskAndFraud";
import { Attribution } from "../screens/Attribution";
import { AIInvestigation } from "../screens/AIInvestigation";
import { Timeline } from "../screens/Timeline";
import { FundFlow } from "../screens/FundFlow";
import { InvestigationGraph } from "../screens/InvestigationGraph";
import { InvestigationReport } from "../screens/InvestigationReport";
import { Evidence } from "../screens/Evidence";
import type { AIResponse } from "../api";
import "./InvestigationWorkspace.css";

interface InvestigationWorkspaceProps {
  caseId: string;
  walletAddress: string;
  data: {
    summary?: any;
    transactions?: any[];
    graph?: any;
    paths?: any[];
    risk?: any;
    attributions?: any[];
    evidence?: any[];
    wallets?: any[];
    aiResponse?: AIResponse | null;
    alerts?: any[];
    advancedIndicators?: {
      defi?: any[];
      bridges?: any[];
      mixers?: any[];
      unknown_contract_label?: string;
    };
    health?: any;
    chain?: string;
    loading?: boolean;
    analyzing?: boolean;
    error?: string | null;
    caseStatus?: {
      progress: number;
      current_stage: string;
      status: string;
      error?: string | null;
    };
  };
  onNavigate?: (screen: string) => void;
  initialTab?: string;
  onRefresh?: () => void;
  onAskAi?: (question: string) => Promise<AIResponse | null>;
  onAiAction?: (
    action: "summary" | "risk" | "attribution" | "path" | "nextSteps",
  ) => Promise<AIResponse | null>;
  onExportReport?: () => Promise<void>;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  caseId,
  walletAddress,
  data,
  onNavigate,
  initialTab = "overview",
  onRefresh,
  onAskAi,
  onAiAction,
  onExportReport,
}) => {
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [caseSummaryOpen, setCaseSummaryOpen] = useState(false);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "transactions", label: "Transactions" },
    { id: "fund-flow", label: "Fund Flow" },
    { id: "graph", label: "Graph" },
    { id: "risk", label: "Risk & Fraud" },
    { id: "attribution", label: "Attribution" },
    { id: "evidence", label: "Evidence" },
    { id: "ai", label: "AI Investigation" },
    { id: "timeline", label: "Timeline" },
    { id: "report", label: "Report" },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case "overview":
        return (
          <Overview
            hasActiveCase
            onStartInvestigation={() => onNavigate?.("new-investigation")}
            onOpenWorkspace={() => setActiveTab("graph")}
            onNavigate={(id) => {
              setActiveTab(id);
              onNavigate?.(id);
            }}
            summary={data.summary}
            risk={data.risk}
            recentTransactions={data.transactions?.slice(0, 5)}
            aiSummary={data.aiResponse?.answer}
            health={data.health}
            evidenceCount={data.evidence?.length}
            alerts={data.alerts}
            chain={data.chain}
            caseStatus={data.caseStatus}
          />
        );
      case "transactions":
        return (
          <Transactions
            transactions={data.transactions || []}
            onSelectTransaction={() => onNavigate?.("graph")}
          />
        );
      case "risk":
        return (
          <RiskAndFraud
            score={data.risk?.overall_score || 0}
            level={data.risk?.risk_level || "UNKNOWN"}
            indicators={data.risk?.indicators || []}
            alerts={data.alerts || []}
            advanced={data.advancedIndicators}
            attributions={data.attributions || []}
            chain={data.chain}
          />
        );
      case "attribution":
        return <Attribution candidates={data.attributions || []} />;
      case "evidence":
        return (
          <Evidence
            items={data.evidence || []}
            transactions={data.transactions || []}
          />
        );
      case "ai":
        return (
          <AIInvestigation
            caseId={caseId}
            response={data.aiResponse}
            health={data.health}
            onAsk={onAskAi}
            onAction={onAiAction}
          />
        );
      case "timeline":
        return (
          <Timeline
            transactions={data.transactions || []}
            risk={data.risk}
          />
        );
      case "fund-flow":
        return (
          <FundFlow
            paths={data.paths || []}
            transactions={data.transactions || []}
            risk={data.risk}
            seedWallet={walletAddress}
          />
        );
      case "graph":
        return (
          <InvestigationGraph
            graph={data.graph}
            attributions={data.attributions || []}
            risk={data.risk}
            seedWallet={walletAddress}
            wallets={data.wallets || []}
            loading={data.loading}
            error={data.error}
          />
        );
      case "report":
        return (
          <InvestigationReport
            caseId={caseId}
            walletAddress={walletAddress}
            chain={data.chain}
            summary={data.summary}
            risk={data.risk}
            attributions={data.attributions || []}
            recentTransactions={data.transactions?.slice(0, 5) || []}
            evidence={data.evidence || []}
            aiSummary={data.aiResponse?.answer}
            aiStatus={data.aiResponse?.provider_status}
            realMode={Boolean(data.health?.real_mode)}
            onExport={onExportReport}
          />
        );
      default:
        return <div>This section is under development.</div>;
    }
  };

  return (
    <div className="workspace">
      <div
        className={`workspace__sidebar ${caseSummaryOpen ? "workspace__sidebar--open" : ""}`}
      >
        <CaseSummary
          caseId={caseId}
          walletAddress={walletAddress}
          risk={data.risk?.overall_score || 0}
          status={
            data.caseStatus?.current_stage ||
            (data.health?.real_mode ? "REAL" : "DEMO")
          }
          stats={{
            transactionsAnalyzed: data.transactions?.length || 0,
            connectedWallets: data.graph?.nodes?.length || data.wallets?.length || 0,
            suspiciousEntities: data.summary?.suspiciousEntities || 0,
            potentialVASPs: data.summary?.potentialVASPs || 0,
            evidenceItems: data.evidence?.length || 0,
            progress: data.caseStatus?.progress ?? 0,
          }}
        />
        {onRefresh && (
          <button className="workspace__tab" onClick={onRefresh}>
            Refresh case
          </button>
        )}
      </div>

      <div className="workspace__main">
        <div className="workspace__tabs" role="tablist" aria-label="Investigation tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              className={`workspace__tab ${
                activeTab === tab.id ? "workspace__tab--active" : ""
              }`}
              onClick={() => {
                setActiveTab(tab.id);
                onNavigate?.(tab.id);
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div
          className="workspace__content"
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
        >
          {renderTabContent()}
        </div>
      </div>

      <button
        className="workspace__sidebar-toggle"
        onClick={() => setCaseSummaryOpen(!caseSummaryOpen)}
      >
        📋
      </button>
    </div>
  );
};
