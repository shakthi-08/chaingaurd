# ChainGuard Frontend — Quick Start Guide

## Getting Started

### Prerequisites
- Node.js 16+ (check with `node --version`)
- npm 7+ (check with `npm --version`)

### Installation & Running

```bash
# 1. Navigate to project directory
cd chainguard-frontend-new

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```

The app will open at **http://localhost:5173** in your default browser.

### What You'll See

1. **Sidebar** (left): Navigation menu with 12 options
2. **Top Bar** (top): Case strip showing case ID, wallet, risk, status
3. **Content Area** (center): Investigative screens
4. **Case Summary** (side panel when in workspace): Investigation metadata

### Exploring the Screens

**Main Navigation (Sidebar)**
- **Overview** — Dashboard with metrics, risk summary, recent transactions
- **New Investigation** — Enter wallet address to start investigation
- **Investigations** — List of cases (stub, not yet active case selection)
- **Transactions** — Full evidence table with search/filter/detail drawer
- **Fund Flow** — *(Requires active case)* Directional transaction flow visualization
- **Investigation Graph** — *(Requires active case)* Full network with filtering
- **Risk & Fraud** — Deep dive into risk scoring
- **Attribution** — Entity identification with confidence
- **AI Investigation** — AI-assisted findings (cyan-marked)
- **Timeline** — Investigation progress events
- **System Status** — Real-time system health

### Available Commands

```bash
# Development server (with hot reload)
npm run dev

# Production build (output in dist/)
npm run build

# Preview production build locally
npm run preview

# Run tests
npm run test
```

### Backend Integration

The app proxies API calls to `http://127.0.0.1:8000` by default (see vite.config.ts).

To use a different backend:
```bash
# Set environment variables
export VITE_API_BASE=https://your-backend-url/api
export VITE_WS_BASE=wss://your-backend-url

# Then run dev server
npm run dev
```

### Key Features Implemented

✅ **Fund Flow Visualization** (Phase 8)
- Interactive ReactFlow graph showing transaction paths
- Path selection with metrics
- Edge thickness scaled to transaction value
- Risk-based color coding

✅ **Investigation Graph** (Phase 9)
- Full network visualization with node types
- Interactive filtering by node classification
- Detail drawer with attribution info
- Selection-based path highlighting

✅ **Investigation Report** (Phase 14)
- Formal document view
- Print/PDF export ready
- Professional formatting

✅ **Accessibility** (WCAG 2.1 AA)
- Keyboard navigation throughout
- Screen reader compatible
- Proper focus management
- ARIA labels and roles

✅ **Responsive Design**
- Desktop: 3-pane layout
- Tablet: Sidebar collapses to icons
- Mobile: Full-width, hamburger menu

### Troubleshooting

**Port 5173 already in use?**
```bash
# Kill the process using port 5173
# On Windows:
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# On macOS/Linux:
lsof -ti:5173 | xargs kill -9
```

**Backend connection fails?**
- Ensure backend is running on http://127.0.0.1:8000
- Check VITE_API_BASE environment variable
- Open DevTools (F12) → Network tab → check /api calls

**Blank screen or errors?**
- Check browser console (F12) for errors
- Clear browser cache and reload
- Try `npm install` again to reinstall dependencies

### Project Structure

```
src/
├── components/
│   ├── BaseComponents.tsx     # 12 reusable UI components
│   ├── Layout.tsx             # Sidebar, TopBar, CaseSummary
│   ├── InvestigationWorkspace.tsx  # Tabbed interface
│   └── *.css                  # Component styles
├── screens/
│   ├── Overview.tsx           # Dashboard
│   ├── NewInvestigation.tsx   # Wallet intake
│   ├── Transactions.tsx       # Evidence table
│   ├── RiskAndFraud.tsx       # Risk deep-dive
│   ├── Attribution.tsx        # Entity identification
│   ├── AIInvestigation.tsx    # AI findings
│   ├── Timeline.tsx           # Progress tracker
│   ├── FundFlow.tsx           # ← NEW (Phase 8)
│   ├── InvestigationGraph.tsx # ← NEW (Phase 9)
│   ├── InvestigationReport.tsx # ← NEW (Phase 14)
│   └── *.css                  # Screen styles
├── styles/
│   └── theme.css              # Design system tokens
├── api.ts                     # Backend API client
├── App.tsx                    # Main router
└── main.tsx                   # React entry point
```

### Documentation Files

- **README.md** — Project overview
- **COMPONENTS.md** — Component library reference
- **ACCESSIBILITY_AUDIT.md** — WCAG 2.1 AA audit results
- **IMPLEMENTATION_REPORT.md** — Full implementation details

### Key Technologies

- **React 18+** — UI framework
- **TypeScript** — Type safety (strict mode)
- **Vite 8.2.2** — Build tool & dev server
- **ReactFlow** — Graph visualization
- **Lucide React** — Icon library
- **CSS Modules** — Component styling
- **CSS Variables** — Design tokens

### Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Performance Metrics

- Build: 251ms
- Dev server startup: <500ms
- Bundle size: 391KB JS (gzipped 119KB), 55.75KB CSS (gzipped 8.57KB)
- Time to Interactive: <2s (with network throttling)

### Need Help?

1. Check [COMPONENTS.md](COMPONENTS.md) for component usage
2. Review [ACCESSIBILITY_AUDIT.md](ACCESSIBILITY_AUDIT.md) for features
3. See [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md) for full details
4. Check DevTools console (F12) for error messages

---

**Happy investigating! 🔍**
