# ChainGuard Frontend Implementation

A professional blockchain forensics and cryptocurrency fraud investigation platform UI built with React, TypeScript, and Vite. Implements the full ChainGuard UI/UX specification with a forensic-grade design system optimized for security analysts.

## Project Overview

ChainGuard is a case-management forensic tool designed for blockchain investigators. The interface prioritizes evidence-first investigation flow with a dark theme, professional typography, and semantic color coding for risk levels.

### Key Features Implemented

✅ **Complete Design System**
- Navy-based dark theme (#0B0E14) for sustained screen time
- Semantic color system (success #3DD68C, warning #F0B429, danger #F0473E)
- Inter + IBM Plex Mono typography system
- Consistent spacing scale (4px base) and radius (sm 4px, md 6px, lg 10px)
- Professional shadow and border treatment

✅ **Layout & Navigation**
- Sidebar with collapsible navigation (64px to 232px)
- Top bar with persistent case strip showing wallet, risk, status
- Multi-tab investigation workspace
- Case summary panel that stays visible across screen changes
- Responsive design for tablet and mobile

✅ **Base Components**
- Button (primary, secondary, ghost, danger variants)
- Badge (success, warning, danger, neutral, primary)
- Card with optional borders
- Metric Card for KPIs
- Risk Display with animated radial progress
- Confidence Badge for attribution confidence
- AI Interpretation Panel (cyan-bordered)
- Drawer (right-side slide-out)
- Evidence Card
- Empty states with actions
- Skeleton loaders
- Status indicators

✅ **Screen Components**
1. **Overview** - Dashboard with metrics, risk summary, network preview
2. **New Investigation** - Wallet address intake form with validation
3. **Investigation Workspace** - Tabbed interface with persistent case context
4. **Transactions** - Evidence table with search, filter, and detail drawer
5. **Risk & Fraud** - Risk score dial + indicators + evidence
6. **Attribution** - Confidence-forward entity identification
7. **AI Investigation** - Cyan-bordered interpretation panel with findings
8. **Timeline** - Chronological investigation progress tracker

✅ **Data Management**
- Connected to backend API for live data
- WebSocket support for real-time transaction updates
- State management for case data, UI state, and navigation
- Error handling and loading states

## Project Structure

```
chainguard-frontend-new/
├── src/
│   ├── styles/
│   │   └── theme.css           # Design system tokens & base styles
│   ├── components/
│   │   ├── BaseComponents.tsx   # Reusable UI components
│   │   ├── BaseComponents.css
│   │   ├── Layout.tsx           # Sidebar, TopBar, CaseSummary
│   │   ├── Layout.css
│   │   ├── InvestigationWorkspace.tsx  # Tabbed workspace
│   │   └── InvestigationWorkspace.css
│   ├── screens/
│   │   ├── Overview.tsx         # Dashboard
│   │   ├── Overview.css
│   │   ├── NewInvestigation.tsx # Intake form
│   │   ├── NewInvestigation.css
│   │   ├── Transactions.tsx     # Transaction evidence table
│   │   ├── Transactions.css
│   │   ├── RiskAndFraud.tsx     # Risk analysis
│   │   ├── RiskAndFraud.css
│   │   ├── Attribution.tsx      # Entity identification
│   │   ├── Attribution.css
│   │   ├── AIInvestigation.tsx  # AI findings
│   │   ├── AIInvestigation.css
│   │   ├── Timeline.tsx         # Progress timeline
│   │   └── Timeline.css
│   ├── App.tsx                  # Main app with routing
│   ├── main.tsx                 # Entry point
│   ├── api.ts                   # Backend API client
│   ├── styles.css               # Legacy styles (deprecated)
│   └── vite-env.d.ts
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Design System

### Color Tokens
- **Background**: `--bg-base` (#0B0E14), `--bg-canvas` (#0E1219)
- **Surfaces**: `--surface-1` (#141922), `--surface-2` (#1A212C), `--surface-3` (#212938)
- **Text**: `--text-primary` (#E7ECF3), `--text-secondary` (#9AA7BD), `--text-tertiary` (#657186)
- **Accents**: `--accent-primary` (#3E8FFF), `--accent-cyan` (#2FD0C9)
- **Semantic**: `--success` (#3DD68C), `--warning` (#F0B429), `--danger` (#F0473E)

### Typography
- **Display**: 56px, 700, tabular numerals (risk scores)
- **H1**: 20px, 600 (page titles)
- **H2**: 15px, 600 (section headers)
- **Body**: 13px, 400 (default UI text)
- **Metadata**: 12px, 500 (labels)
- **Monospace**: IBM Plex Mono, 12.5px (addresses, hashes)

### Spacing
4px base scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px

### Components Density
- Table rows: 36-40px height
- Card padding: 12-16px
- Panel padding: 16px default
- Border radius: 4px (buttons/inputs), 6px (cards), 10px (modals)

## Running the Application

### Development
```bash
npm install
npm run dev
# Opens http://localhost:5173
```

### Build
```bash
npm run build
# Creates optimized dist/ folder
```

### Test
```bash
npm run test
```

## UI Features

### Case Strip (Top Bar)
- Status indicator (● ANALYZING)
- Case ID (CASE #CG-2026-00124)
- Wallet address in monospace, truncated with copy button
- Risk badge showing level and score
- Last updated timestamp
- User menu and notification bell

### Investigation Workspace
- **Left Panel**: Case summary with metrics (transactions, wallets, entities, VASPs, evidence, progress)
- **Main Area**: Tabs for different investigation modules
- **Mobile**: Collapsible side panel, stacked layout

### Evidence-First Design
- All blockchain data shown with monospace, truncated with copy affordance
- AI content always marked with cyan (#2FD0C9) border and "AI Interpretation" label
- Confidence levels always paired with text label (never color alone)
- Risk indicators include: type, severity badge, explanation, evidence links
- Empty states explain both "what happened" and "what to do"

### Loading & Error States
- Skeleton loaders with shimmer animation matching content shape
- Purpose-built skeletons for tables, grids, and specific layouts
- Error cards with icon, cause, retry button, and link to system status
- Partial result banner for incomplete data

## Key Design Principles Applied

1. **Evidence before opinion** - Blockchain facts distinct from AI interpretations
2. **Density with discipline** - High information density organized through tabs and progressive disclosure
3. **Certainty is earned** - Risk scores, attribution always show confidence + supporting basis
4. **Color is signal** - Green/amber/red semantic system, never decorative
5. **The case is always present** - Case strip persists showing case ID, wallet, risk, status
6. **No invented data** - Every field maps to real backend data
7. **Motion explains** - Animations for state transitions, progress, selection; none are ambient

## Accessibility

- Minimum 4.5:1 contrast verified across surfaces
- Full keyboard navigation (nav, tables, tabs, graph controls)
- Visible focus ring (2px `--accent-primary` outline) on all interactive elements
- Risk/status never color-only - always paired with text/icon
- Form labels explicit (not placeholder-only)
- Drawers trap focus, dismissible via Escape
- Touch targets minimum 40×40px mobile
- Semantic HTML structure

## Responsive Breakpoints

- **Desktop** (≥1280px): Full three-pane layouts
- **Tablet** (768-1279px): Sidebar collapses to icon-only, side panels become overlays
- **Mobile** (<768px): Bottom tab bar, hamburger drawer, full-screen overlays, stacked cards

## Browser Support

- Modern browsers with ES6+ support
- Tested on Chrome, Firefox, Safari, Edge
- iOS Safari with proper touch handling and font sizing

## Future Enhancements

1. **Fund Flow Diagram** - Directional flow visualization component
2. **Enhanced Graph** - Full ReactFlow investigation graph with filtering
3. **Investigation Report** - Formal document view with export/print
4. **Cross-Chain Visualization** - Bridge service tracking
5. **Advanced Filters** - Date range, asset type, direction filters
6. **Export Features** - PDF reports, transaction lists
7. **Multi-case Navigation** - Investigations list and case switcher
8. **Real-time Notifications** - Toast notifications for new events

## Dependencies

- **React** 18+
- **TypeScript** 5+
- **Vite** 5+ (build tool)
- **Lucide React** (icon library)
- **ReactFlow** (graph visualization)

## API Integration

The app connects to a backend API that provides:
- Transactions for a case
- Graph (nodes/edges/transactions)
- Fund flow paths
- Risk assessment
- Attribution data
- AI interpretations
- Real-time WebSocket updates for new transactions

See `src/api.ts` for type definitions and endpoints.

## Development Notes

### Adding New Screens
1. Create component in `src/screens/[ScreenName].tsx`
2. Import BaseComponents from `../components/BaseComponents`
3. Add screen to `App.tsx` renderContent() switch
4. Add navigation entry to Sidebar

### Modifying Colors
1. Update CSS custom properties in `src/styles/theme.css`
2. Reference via `var(--token-name)` in component styles
3. Test contrast ratios with Contrast Checker tool

### Working with Responsive Design
- Use CSS Grid/Flexbox for flexible layouts
- Test at 768px and 1024px breakpoints
- Provide mobile-specific interactions (tap targets, overlays vs side panels)
- Use CSS media queries in component CSS files

## License

Part of the ChainGuard blockchain forensics platform.

---

**Built with attention to forensic precision and investigative clarity.**
