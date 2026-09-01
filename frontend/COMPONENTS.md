# ChainGuard Component Library

Complete reference guide for all components implemented in the ChainGuard frontend.

## Base Components (`src/components/BaseComponents.tsx`)

### Button
A versatile button component with multiple variants and sizes.

```tsx
import { Button } from "./components/BaseComponents";

<Button variant="primary" size="md" onClick={() => {}}>
  Start Investigation
</Button>

<Button variant="danger" size="sm" onClick={() => {}}>
  Delete Case
</Button>
```

**Props:**
- `variant`: "primary" | "secondary" | "ghost" | "danger" (default: "primary")
- `size`: "sm" | "md" | "lg" (default: "md")
- `children`: ReactNode
- `...buttonProps`: All HTML button attributes

---

### Badge
Small labeled tag component for status and categories.

```tsx
<Badge variant="success">Verified</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="danger">High Risk</Badge>
```

**Props:**
- `variant`: "success" | "warning" | "danger" | "neutral" | "primary"
- `children`: ReactNode
- `className`: string (optional)

---

### Card
Container component for grouping related content.

```tsx
<Card bordered={true}>
  <h3>Risk Summary</h3>
  <p>Content here...</p>
</Card>
```

**Props:**
- `children`: ReactNode
- `className`: string (optional)
- `bordered`: boolean (default: true)

---

### MetricCard
Displays a labeled metric with optional delta and icon.

```tsx
<MetricCard
  label="Transactions Analyzed"
  value={247}
  icon={<Database size={16} />}
  delta={{ value: 12, type: "positive" }}
/>
```

**Props:**
- `label`: string
- `value`: string | number
- `delta`: { value: number; type: "positive" | "negative" } (optional)
- `icon`: ReactNode (optional)
- `className`: string (optional)

---

### RiskDisplay
Animated risk score dial showing 0-100 score with gradient color.

```tsx
<RiskDisplay
  score={87}
  label="87 / 100 — HIGH RISK"
/>
```

**Props:**
- `score`: number (0-100)
- `label`: string
- `className`: string (optional)

---

### ConfidenceBadge
Shows confidence percentage with qualitative label.

```tsx
<ConfidenceBadge confidence={0.85} />
// Renders: "85% High Confidence"
```

**Props:**
- `confidence`: number (0-1)
- `className`: string (optional)

---

### AIInterpretationPanel
Cyan-bordered panel for AI-generated content with distinct visual treatment.

```tsx
<AIInterpretationPanel>
  <p>This AI interpretation is based on pattern matching...</p>
</AIInterpretationPanel>
```

**Props:**
- `children`: ReactNode
- `className`: string (optional)

---

### Drawer
Right-side slide-out panel for detailed information.

```tsx
const [isOpen, setIsOpen] = useState(false);

<Drawer
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  title="Transaction Details"
>
  <div>Content...</div>
</Drawer>
```

**Props:**
- `isOpen`: boolean
- `onClose`: () => void
- `title`: string (optional)
- `children`: ReactNode
- `className`: string (optional)

---

### EvidenceCard
Displays a piece of evidence with source, excerpt, and link.

```tsx
<EvidenceCard
  source="TX_HASH_ABC123"
  excerpt="Suspicious pattern detected in fund flow"
  link="/tx/abc123"
/>
```

**Props:**
- `source`: string
- `excerpt`: string
- `link`: string (optional)
- `className`: string (optional)

---

### EmptyState
Standardized empty state with icon, heading, description, and action.

```tsx
<EmptyState
  icon={<Search size={48} />}
  heading="No transactions found"
  description="Try adjusting your filters"
  action={{
    label: "Clear Filters",
    onClick: () => setFilters({})
  }}
/>
```

**Props:**
- `icon`: ReactNode (optional)
- `heading`: string
- `description`: string
- `action`: { label: string; onClick: () => void } (optional)
- `className`: string (optional)

---

### SkeletonLoader
Shimmer-animated loading placeholder.

```tsx
<SkeletonLoader rows={8} />
```

**Props:**
- `rows`: number (default: 8)
- `className`: string (optional)

---

### StatusIndicator
Shows connection status with animated dot.

```tsx
<StatusIndicator status="connected" />
// Options: "connecting" | "connected" | "disconnected"
```

**Props:**
- `status`: "connecting" | "connected" | "disconnected"

---

## Layout Components (`src/components/Layout.tsx`)

### Sidebar
Navigation sidebar with collapsible state and real-time status.

```tsx
<Sidebar
  activeNav="overview"
  onNavChange={(navId) => setCurrentNav(navId)}
  isCollapsed={false}
  onToggleCollapse={() => setCollapsed(!collapsed)}
  hasActiveCase={true}
  realtimeStatus="connected"
/>
```

**Props:**
- `activeNav`: string
- `onNavChange`: (navId: string) => void
- `isCollapsed`: boolean (optional)
- `onToggleCollapse`: () => void (optional)
- `hasActiveCase`: boolean (optional)
- `realtimeStatus`: "connecting" | "connected" | "disconnected" (optional)

---

### TopBar
Header bar with optional case strip and user controls.

```tsx
<TopBar
  caseId="CASE-DEMO-001"
  walletAddress="0x1111...1111"
  riskScore={87}
  status="ANALYZING"
  onNotifications={() => {}}
  onUserMenu={() => {}}
/>
```

**Props:**
- `caseId`: string (optional)
- `walletAddress`: string (optional)
- `riskScore`: number (optional)
- `status`: string (optional)
- `onNotifications`: () => void (optional)
- `onUserMenu`: () => void (optional)

---

### Layout
Main layout wrapper combining Sidebar, TopBar, and content area.

```tsx
<Layout
  activeNav={currentScreen}
  onNavChange={handleNavChange}
  caseId={CASE_ID}
  walletAddress={WALLET}
  riskScore={risk}
  hasActiveCase={true}
>
  {children}
</Layout>
```

**Props:**
- `children`: ReactNode
- `activeNav`: string
- `onNavChange`: (navId: string) => void
- `sidebarCollapsed`: boolean (optional)
- `onToggleSidebar`: () => void (optional)
- `caseId`: string (optional)
- `walletAddress`: string (optional)
- `riskScore`: number (optional)
- `hasActiveCase`: boolean (optional)
- `realtimeStatus`: RealtimeStatus (optional)

---

### CaseSummary
Sidebar panel showing case metadata and quick stats.

```tsx
<CaseSummary
  caseId="CASE-DEMO-001"
  walletAddress="0x1111...1111"
  risk={87}
  status="ANALYZING"
  stats={{
    transactionsAnalyzed: 247,
    connectedWallets: 18,
    suspiciousEntities: 5,
    potentialVASPs: 3,
    evidenceItems: 12,
    progress: 85
  }}
/>
```

**Props:**
- `caseId`: string
- `walletAddress`: string
- `risk`: number
- `status`: string
- `stats`: object with 6 numeric properties

---

## Screen Components (`src/screens/`)

### Overview
Dashboard showing case metrics, risk summary, and recent activity.

```tsx
<Overview
  hasActiveCase={true}
  onStartInvestigation={() => navigate('/new')}
  summary={{ transactions: 247, wallets: 18, ... }}
  risk={{ overall_score: 87, risk_level: "HIGH", ... }}
  recentTransactions={[...]}
  aiSummary="Suspicious fund flow detected..."
/>
```

### NewInvestigation
Wallet address intake form for starting a new investigation.

```tsx
<NewInvestigation
  onSubmit={(walletAddress) => handleStartCase(walletAddress)}
  isLoading={false}
/>
```

### Transactions
Evidence table with search, filter, and detail drawer.

```tsx
<Transactions
  transactions={[...]}
  onSelectTransaction={(tx) => handleSelectTx(tx)}
/>
```

### RiskAndFraud
Risk score dial, indicators, and supporting evidence.

```tsx
<RiskAndFraud
  score={87}
  level="HIGH"
  indicators={[...]}
/>
```

### Attribution
Confidence-forward entity identification with alternatives.

```tsx
<Attribution
  candidates={[
    {
      entity: "Binance US",
      entity_type: "Exchange",
      confidence: 0.92,
      ...
    }
  ]}
/>
```

### AIInvestigation
AI findings with confidence levels, reasoning, and limitations.

```tsx
<AIInvestigation
  interpretation="Pattern analysis suggests..."
  findings={[...]}
  explanation="Detailed reasoning..."
  isLoading={false}
/>
```

### Timeline
Chronological progress tracker with status markers.

```tsx
<Timeline
  events={[
    {
      id: "1",
      timestamp: new Date().toISOString(),
      event: "Investigation started",
      status: "complete"
    },
    ...
  ]}
/>
```

---

## Workspace Component (`src/components/InvestigationWorkspace.tsx`)

### InvestigationWorkspace
Tabbed interface for investigation modules with persistent case sidebar.

```tsx
<InvestigationWorkspace
  caseId="CASE-DEMO-001"
  walletAddress="0x1111...1111"
  data={{
    summary: {...},
    transactions: [...],
    graph: {...},
    risk: {...},
    attributions: [...],
    aiResponse: {...}
  }}
/>
```

**Features:**
- 9 tabs: Overview, Transactions, Fund Flow, Graph, Risk, Attribution, AI, Timeline, Report
- Persistent left sidebar showing case summary
- Tab switching preserves scroll position
- Mobile-responsive with collapsible sidebar

---

## Usage Patterns

### Building a New Screen

1. **Import components**
```tsx
import { Card, Button, Badge } from "../components/BaseComponents";
import "./MyScreen.css";
```

2. **Create screen component**
```tsx
export const MyScreen: React.FC<MyScreenProps> = ({ data }) => {
  return (
    <div className="my-screen">
      <Card>
        <h2>Title</h2>
        <p>Content...</p>
        <Button onClick={() => {}}>Action</Button>
      </Card>
    </div>
  );
};
```

3. **Add to App.tsx**
```tsx
case "my-screen":
  return <MyScreen data={data} />;
```

### Working with Data Flow

```tsx
// In App.tsx
const [caseData, setCaseData] = useState<CaseData>(null);

useEffect(() => {
  loadCaseData().then(setCaseData);
}, [caseId]);

// Pass to children
<InvestigationWorkspace data={caseData} />

// In children
<RiskDisplay score={data.risk.overall_score} />
```

### Responsive Patterns

```css
/* Desktop */
.container {
  display: grid;
  grid-template-columns: 240px 1fr;
}

/* Tablet */
@media (max-width: 1024px) {
  .container {
    display: flex;
    flex-direction: column;
  }
  .sidebar {
    position: fixed;
    left: -100%;
  }
}

/* Mobile */
@media (max-width: 768px) {
  .tabs {
    flex-wrap: wrap;
  }
}
```

---

## Color Reference

Use CSS custom properties for all colors:

```tsx
// In CSS
color: var(--text-primary);       // #E7ECF3
background: var(--surface-2);     // #1A212C
border-color: var(--border-subtle); // #26303F

// Risk colors
.risk-high { color: var(--danger); }        // #F0473E
.risk-medium { color: var(--warning); }    // #F0B429
.risk-low { color: var(--success); }       // #3DD68C

// AI content indicator
border-left: 2px solid var(--accent-cyan); // #2FD0C9
```

---

## Theming

To customize the theme, edit `src/styles/theme.css`:

```css
:root {
  --bg-base: #0b0e14;
  --text-primary: #e7ecf3;
  --accent-primary: #3e8fff;
  /* ... etc */
}
```

All components use these tokens, so theme changes apply globally.

---

## Accessibility Checklist

- [ ] All interactive elements have visible focus rings
- [ ] Text contrast is ≥4.5:1
- [ ] Form inputs have explicit labels
- [ ] Risk/status never shown as color-only
- [ ] Focus order is logical
- [ ] Modals trap focus
- [ ] Touch targets ≥40×40px
- [ ] Images have alt text
- [ ] Drawers dismiss via Escape key

---

## Performance Tips

- Use memoization for expensive computations
- Lazy load screen components
- Virtualize long lists in tables
- Avoid re-renders of large graph visualizations
- Cache API responses appropriately

---

Built with precision for blockchain forensics professionals.
