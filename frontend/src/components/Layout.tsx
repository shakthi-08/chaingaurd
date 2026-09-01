import React, { ReactNode } from 'react';
import {
  Home,
  Plus,
  FileText,
  ArrowRightLeft,
  TrendingUp,
  Network,
  AlertTriangle,
  Target,
  Zap,
  Clock,
  BarChart3,
  Settings,
  Bell,
  User,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import './Layout.css';

interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', icon: <Home size={20} />, label: 'Overview' },
  { id: 'new-investigation', icon: <Plus size={20} />, label: 'New Investigation' },
  { id: 'investigations', icon: <FileText size={20} />, label: 'Investigations' },
  { id: 'transactions', icon: <ArrowRightLeft size={20} />, label: 'Transactions' },
  { id: 'fund-flow', icon: <TrendingUp size={20} />, label: 'Fund Flow' },
  { id: 'graph', icon: <Network size={20} />, label: 'Investigation Graph' },
  { id: 'risk', icon: <AlertTriangle size={20} />, label: 'Risk & Fraud' },
  { id: 'attribution', icon: <Target size={20} />, label: 'Attribution' },
  { id: 'ai', icon: <Zap size={20} />, label: 'AI Investigation' },
  { id: 'timeline', icon: <Clock size={20} />, label: 'Timeline' },
  { id: 'report', icon: <BarChart3 size={20} />, label: 'Investigation Report' },
  { id: 'status', icon: <Settings size={20} />, label: 'System Status', disabled: true },
];

interface SidebarProps {
  activeNav: string;
  onNavChange: (navId: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  hasActiveCase?: boolean;
  realtimeStatus?: 'connecting' | 'connected' | 'disconnected';
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeNav,
  onNavChange,
  isCollapsed = false,
  onToggleCollapse,
  hasActiveCase = false,
  realtimeStatus = 'disconnected',
}) => {
  const getStatusColor = () => {
    switch (realtimeStatus) {
      case 'connected':
        return 'var(--success)';
      case 'connecting':
        return 'var(--warning)';
      default:
        return 'var(--danger)';
    }
  };

  return (
    <aside className={`sidebar ${isCollapsed ? 'sidebar--collapsed' : ''}`}>
      <div className="sidebar__header">
        <div className="sidebar__branding">
          {!isCollapsed && (
            <>
              <div className="sidebar__logo">⛓️</div>
              <span className="sidebar__title">ChainGuard</span>
            </>
          )}
        </div>
      </div>

      <nav className="sidebar__nav" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => {
          const isDisabled = Boolean(item.disabled) && !hasActiveCase;
          return (
            <button
              key={item.id}
              className={`sidebar__nav-item ${
                activeNav === item.id ? 'sidebar__nav-item--active' : ''
              } ${isDisabled ? 'sidebar__nav-item--disabled' : ''}`}
              onClick={() => !isDisabled && onNavChange(item.id)}
              disabled={isDisabled}
              title={item.label}
              aria-current={activeNav === item.id ? 'page' : undefined}
            >
              <span className="sidebar__nav-icon">{item.icon}</span>
              {!isCollapsed && (
                <>
                  <span className="sidebar__nav-label">{item.label}</span>
                  {isDisabled && (
                    <span className="sidebar__nav-lock" title="Requires active investigation">
                      🔒
                    </span>
                  )}
                </>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__status">
          <span
            className="sidebar__status-dot"
            style={{ backgroundColor: getStatusColor() }}
          />
          {!isCollapsed && (
            <span className="sidebar__status-label">
              {realtimeStatus === 'connected'
                ? 'Connected'
                : realtimeStatus === 'connecting'
                  ? 'Connecting'
                  : 'Offline'}
            </span>
          )}
        </div>
        {onToggleCollapse && (
          <button
            className="sidebar__toggle"
            onClick={onToggleCollapse}
            aria-label="Toggle sidebar"
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        )}
      </div>
    </aside>
  );
};

/* Top Bar Component */
interface TopBarProps {
  caseId?: string;
  walletAddress?: string;
  riskScore?: number;
  status?: string;
  onNotifications?: () => void;
  onUserMenu?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  caseId,
  walletAddress,
  riskScore,
  status,
  onNotifications,
  onUserMenu,
}) => {
  const getRiskColor = (score?: number) => {
    if (!score) return 'var(--text-secondary)';
    if (score < 50) return 'var(--success)';
    if (score < 80) return 'var(--warning)';
    return 'var(--danger)';
  };

  const getRiskLabel = (score?: number) => {
    if (!score) return 'UNKNOWN';
    if (score < 50) return 'LOW';
    if (score < 80) return 'MEDIUM';
    return 'HIGH';
  };

  return (
    <div className="top-bar">
      {caseId && walletAddress ? (
        <div className="top-bar__case-strip">
          <div className="top-bar__status-indicator">
            <span className="top-bar__status-dot" />
            <span className="top-bar__status-label">{status || 'ACTIVE'}</span>
          </div>
          <span className="top-bar__case-id">{caseId}</span>
          <div className="top-bar__wallet">
            <code className="monospace">{walletAddress.slice(0, 8)}...{walletAddress.slice(-6)}</code>
            <button className="top-bar__copy" title="Copy address" aria-label="Copy wallet address">
              📋
            </button>
          </div>
          <div className="top-bar__separator" />
          {riskScore !== undefined && (
            <div
              className="top-bar__risk"
              style={{ color: getRiskColor(riskScore) }}
            >
              RISK: <strong>{getRiskLabel(riskScore)}</strong> ({riskScore})
            </div>
          )}
          <div className="top-bar__timestamp">
            Updated {new Date().toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <div className="top-bar__empty">No active investigation</div>
      )}

      <div className="top-bar__controls">
        <button
          className="top-bar__control-btn"
          onClick={onNotifications}
          title="Notifications"
          aria-label="Open notifications"
        >
          <Bell size={18} />
        </button>
        <button
          className="top-bar__control-btn"
          onClick={onUserMenu}
          title="User menu"
          aria-label="Open user menu"
        >
          <User size={18} />
        </button>
      </div>
    </div>
  );
};

/* Main Layout Component */
interface LayoutProps {
  children: ReactNode;
  activeNav: string;
  onNavChange: (navId: string) => void;
  sidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
  caseId?: string;
  walletAddress?: string;
  riskScore?: number;
  hasActiveCase?: boolean;
  realtimeStatus?: 'connecting' | 'connected' | 'disconnected';
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  activeNav,
  onNavChange,
  sidebarCollapsed = false,
  onToggleSidebar,
  caseId,
  walletAddress,
  riskScore,
  hasActiveCase = false,
  realtimeStatus = 'disconnected',
}) => {
  return (
    <div className="layout">
      <Sidebar
        activeNav={activeNav}
        onNavChange={onNavChange}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={onToggleSidebar}
        hasActiveCase={hasActiveCase}
        realtimeStatus={realtimeStatus}
      />
      <div className="layout__main">
        <TopBar
          caseId={caseId}
          walletAddress={walletAddress}
          riskScore={riskScore}
          status={realtimeStatus === 'connected' ? 'ANALYZING' : 'PAUSED'}
        />
        <main className="layout__content">{children}</main>
      </div>
    </div>
  );
};

/* Case Summary Panel (for workspace sidebar) */
interface CaseSummaryProps {
  caseId: string;
  walletAddress: string;
  risk: number;
  status: string;
  stats: {
    transactionsAnalyzed: number;
    connectedWallets: number;
    suspiciousEntities: number;
    potentialVASPs: number;
    evidenceItems: number;
    progress: number;
  };
}

export const CaseSummary: React.FC<CaseSummaryProps> = ({
  caseId,
  walletAddress,
  risk,
  status,
  stats,
}) => {
  return (
    <div className="case-summary">
      <div className="case-summary__header">
        <h3>Investigation</h3>
      </div>

      <div className="case-summary__section">
        <div className="case-summary__label">Case ID</div>
        <code className="case-summary__value monospace">{caseId}</code>
      </div>

      <div className="case-summary__section">
        <div className="case-summary__label">Wallet Address</div>
        <code className="case-summary__value monospace">
          {walletAddress.slice(0, 8)}...{walletAddress.slice(-6)}
        </code>
      </div>

      <div className="case-summary__section">
        <div className="case-summary__label">Risk Level</div>
        <div
          className="case-summary__risk-badge"
          style={{
            color: risk < 50 ? 'var(--success)' : risk < 80 ? 'var(--warning)' : 'var(--danger)',
          }}
        >
          {risk < 50 ? 'LOW' : risk < 80 ? 'MEDIUM' : 'HIGH'} ({risk})
        </div>
      </div>

      <div className="case-summary__section">
        <div className="case-summary__label">Status</div>
        <div className="case-summary__status">{status}</div>
      </div>

      <div className="case-summary__stats">
        <div className="case-summary__stat">
          <div className="case-summary__stat-label">Transactions</div>
          <div className="case-summary__stat-value">{stats.transactionsAnalyzed}</div>
        </div>
        <div className="case-summary__stat">
          <div className="case-summary__stat-label">Wallets</div>
          <div className="case-summary__stat-value">{stats.connectedWallets}</div>
        </div>
        <div className="case-summary__stat">
          <div className="case-summary__stat-label">Entities</div>
          <div className="case-summary__stat-value">{stats.suspiciousEntities}</div>
        </div>
        <div className="case-summary__stat">
          <div className="case-summary__stat-label">VASPs</div>
          <div className="case-summary__stat-value">{stats.potentialVASPs}</div>
        </div>
        <div className="case-summary__stat">
          <div className="case-summary__stat-label">Evidence</div>
          <div className="case-summary__stat-value">{stats.evidenceItems}</div>
        </div>
        <div className="case-summary__stat">
          <div className="case-summary__stat-label">Progress</div>
          <div className="case-summary__stat-value">{stats.progress}%</div>
        </div>
      </div>
    </div>
  );
};
