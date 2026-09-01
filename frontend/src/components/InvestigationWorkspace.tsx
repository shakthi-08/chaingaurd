import React, { useEffect, useState } from 'react';
import { CaseSummary } from './Layout';
import { Overview } from '../screens/Overview';
import { Transactions } from '../screens/Transactions';
import { RiskAndFraud } from '../screens/RiskAndFraud';
import { Attribution } from '../screens/Attribution';
import { AIInvestigation } from '../screens/AIInvestigation';
import { Timeline } from '../screens/Timeline';
import { FundFlow } from '../screens/FundFlow';
import { InvestigationGraph } from '../screens/InvestigationGraph';
import { InvestigationReport } from '../screens/InvestigationReport';
import './InvestigationWorkspace.css';

interface InvestigationWorkspaceProps {
  caseId: string;
  walletAddress: string;
  data: any;
  onNavigate?: (screen: string) => void;
  initialTab?: string;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  caseId,
  walletAddress,
  data,
  onNavigate,
  initialTab = 'overview',
}) => {
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [caseSummaryOpen, setCaseSummaryOpen] = useState(false);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'transactions', label: 'Transactions' },
    { id: 'fund-flow', label: 'Fund Flow' },
    { id: 'graph', label: 'Graph' },
    { id: 'risk', label: 'Risk & Fraud' },
    { id: 'attribution', label: 'Attribution' },
    { id: 'ai', label: 'AI Investigation' },
    { id: 'timeline', label: 'Timeline' },
    { id: 'report', label: 'Report' },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <Overview
            hasActiveCase
            onStartInvestigation={() => {}}
            summary={data.summary}
            risk={data.risk}
            recentTransactions={data.transactions?.slice(0, 5)}
            aiSummary={data.aiResponse?.answer}
          />
        );
      case 'transactions':
        return (
          <Transactions
            transactions={data.transactions || []}
            onSelectTransaction={() => {}}
          />
        );
      case 'risk':
        return (
          <RiskAndFraud
            score={data.risk?.overall_score || 0}
            level={data.risk?.risk_level || 'UNKNOWN'}
            indicators={data.risk?.indicators || []}
          />
        );
      case 'attribution':
        return (
          <Attribution candidates={data.attributions || []} />
        );
      case 'ai':
        return (
          <AIInvestigation
            interpretation={
              data.aiResponse?.answer ||
              'AI analysis not yet available. Processing investigation data...'
            }
            findings={
              data.risk?.findings?.map((f: any) => ({
                claim: f.type,
                confidence: f.confidence || 0.75,
                evidence_ref: f.transaction_refs?.[0] || 'N/A',
              })) || []
            }
            explanation={data.risk?.explanations?.[0]}
            isLoading={false}
          />
        );
      case 'timeline':
        return (
          <Timeline
            events={[
              {
                id: '1',
                timestamp: new Date(Date.now() - 3600000).toISOString(),
                event: 'Investigation started',
                status: 'complete',
              },
              {
                id: '2',
                timestamp: new Date(Date.now() - 2400000).toISOString(),
                event: 'Blockchain data retrieved',
                status: 'complete',
              },
              {
                id: '3',
                timestamp: new Date(Date.now() - 1800000).toISOString(),
                event: 'Transactions analyzed',
                status: 'complete',
              },
              {
                id: '4',
                timestamp: new Date(Date.now() - 900000).toISOString(),
                event: 'Fund flow traced',
                status: 'complete',
              },
              {
                id: '5',
                timestamp: new Date().toISOString(),
                event: 'Risk assessment calculated',
                status: 'active',
                details: 'Computing risk score...',
              },
            ]}
          />
        );
      case 'fund-flow':
        return (
          <FundFlow
            paths={data.paths || []}
            risk={data.risk}
          />
        );
      case 'graph':
        return (
          <InvestigationGraph
            graph={data.graph}
            attributions={data.attributions || []}
            risk={data.risk}
          />
        );
      case 'report':
        return (
          <InvestigationReport
            caseId={caseId}
            walletAddress={walletAddress}
            summary={data.summary}
            risk={data.risk}
            attributions={data.attributions || []}
            recentTransactions={data.transactions?.slice(0, 5) || []}
            aiSummary={data.aiResponse?.answer}
          />
        );
      default:
        return <div>This section is under development.</div>;
    }
  };

  return (
    <div className="workspace">
      {/* Side panel - Case Summary */}
      <div
        className={`workspace__sidebar ${caseSummaryOpen ? 'workspace__sidebar--open' : ''}`}
      >
        <CaseSummary
          caseId={caseId}
          walletAddress={walletAddress}
          risk={data.risk?.overall_score || 0}
          status="ANALYZING"
          stats={{
            transactionsAnalyzed: data.transactions?.length || 0,
            connectedWallets: data.graph?.nodes?.length || 0,
            suspiciousEntities: data.attributions?.length || 0,
            potentialVASPs: 3,
            evidenceItems: 12,
            progress: 85,
          }}
        />
      </div>

      {/* Main content area */}
      <div className="workspace__main">
        {/* Tabs */}
        <div className="workspace__tabs" role="tablist" aria-label="Investigation tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`tabpanel-${tab.id}`}
              id={`tab-${tab.id}`}
              className={`workspace__tab ${
                activeTab === tab.id ? 'workspace__tab--active' : ''
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

        {/* Tab content */}
        <div 
          className="workspace__content" 
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
        >
          {renderTabContent()}
        </div>
      </div>

      {/* Mobile case summary toggle */}
      <button
        className="workspace__sidebar-toggle"
        onClick={() => setCaseSummaryOpen(!caseSummaryOpen)}
      >
        📋
      </button>
    </div>
  );
};
