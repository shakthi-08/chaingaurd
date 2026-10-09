export type Transaction = {
  tx_hash: string;
  from: string;
  to: string;
  value: string;
  token: string | null;
  timestamp: string;
  block: number | null;
  chain?: string;
  contract_address?: string | null;
  tx_type?: string | null;
};

export type CaseWallet = {
  address: string;
  chain: string;
  labels: string[];
  is_seed: boolean;
  first_seen: string | null;
  last_seen: string | null;
};

export type GraphNode = { id: string; type: string };
export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  tx_ref: string;
  value: string;
  timestamp: string;
  token: string | null;
  chain?: string;
  relation_type?: string;
  contract_address?: string | null;
  tx_type?: string | null;
};
export type Graph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  transactions: GraphEdge[];
  cross_chain?: CrossChainMovement[];
};
export type Path = {
  rank: number;
  start_wallet: string;
  end_wallet: string;
  wallets: string[];
  transactions: string[];
  hop_count: number;
  total_value: string;
  values: string[];
  timestamps: string[];
};
export type RiskIndicator = {
  type: string;
  severity: string;
  score: number;
  weight: number;
  confidence: number;
  explanation: string;
  transaction_refs: string[];
  wallet_addresses: string[];
  evidence_refs: string[];
};
export type RiskAssessment = {
  overall_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  indicators: RiskIndicator[];
  findings: RiskIndicator[];
  explanations: string[];
  evidence_refs: string[];
};
export type Attribution = {
  wallet: string;
  entity: string;
  entity_id: string;
  entity_type: string;
  chain: string;
  confidence: number;
  reasons: string[];
  source: string;
  evidence_refs: string[];
  explanation: string;
  status?: string;
  attribution_type?: string;
  provenance?: string;
  conflicting_evidence?: string[];
};
export type EvidenceItem = {
  evidence_id: string;
  case_id: number | null;
  type: string;
  source: string | null;
  transaction_ref: string | null;
  wallet_ref: string | null;
  timestamp: string | null;
  hash?: string | null;
  description: string | null;
  created_at: string | null;
};
export type AIResponse = {
  answer: string;
  evidence_refs: string[];
  provider: string;
  model: string | null;
  ai_assisted: boolean;
  provider_status: "available" | "unavailable" | "error";
  limitations: string[];
};
export type CrossChainMovement = {
  source_chain: string;
  source_transaction: string;
  source_wallet: string;
  destination_chain: string;
  destination_transaction: string;
  destination_wallet: string;
  bridge_service: string;
  timestamp: string;
  transferred_value: string;
  confidence: number;
  reasons: string[];
  evidence_refs: string[];
  source: string;
  bridge_detected?: boolean;
  destination_confirmed?: boolean;
  note?: string | null;
};
export type InvestigationAlert = {
  id?: number;
  case_id?: string;
  category: string;
  severity: string;
  title: string;
  explanation: string;
  wallet_ref?: string | null;
  transaction_ref?: string | null;
  evidence_refs?: string[];
  timestamp?: string | null;
};

export type AdvancedIndicators = {
  defi: Array<Record<string, unknown>>;
  bridges: Array<Record<string, unknown>>;
  mixers: Array<Record<string, unknown>>;
  unknown_contract_label?: string;
};

export type HealthStatus = {
  status: string;
  service?: string;
  version?: string;
  environment?: string;
  blockchain_provider?: string;
  demo_mode?: boolean;
  real_mode?: boolean;
  operational_chains?: string[];
  architectural_chains?: string[];
  ai_provider?: string;
  ai_configured?: boolean;
  ai_model?: string | null;
};

const configuredApiBase = import.meta.env.VITE_API_BASE?.replace(/\/+$/, "");
const apiBase = configuredApiBase
  ? configuredApiBase.endsWith("/api")
    ? configuredApiBase
    : `${configuredApiBase}/api`
  : "/api";

export function realtimeUrl(caseId: string): string | null {
  const configured = import.meta.env.VITE_WS_BASE?.replace(/\/+$/, "");
  if (configured) return `${configured}/cases/${caseId}/events`;
  if (import.meta.env.PROD) return null;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/cases/${caseId}/events`;
}

export function formatCryptoValue(value: string, token?: string | null): string {
  const raw = String(value || "0");
  const numeric = Number(raw);
  const symbol = token && token !== "native" ? token : "";
  if (!Number.isFinite(numeric)) return `${raw} ${symbol}`.trim();
  if (numeric >= 1e15) {
    return `${(numeric / 1e18).toFixed(4)} ${symbol || "ETH"}`.trim();
  }
  if (numeric >= 1e6) {
    return `${numeric.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${symbol}`.trim();
  }
  return `${raw} ${symbol}`.trim();
}

export function shortHash(value: string, size = 6): string {
  if (!value) return "-";
  if (value.length <= size * 2 + 2) return value;
  return `${value.slice(0, size + 2)}…${value.slice(-size)}`;
}

export function confidencePercent(confidence: number): number {
  if (!Number.isFinite(confidence)) return 0;
  return Math.max(0, Math.min(100, Math.round(confidence)));
}

export function attributionStrength(confidence: number, status?: string): string {
  const label = (status || "").toLowerCase();
  if (label === "verified") return "Strong";
  if (label === "provisional") return "Probable";
  if (label === "lead") return "Possible";
  if (label === "unverified") return "Unknown";
  const pct = confidencePercent(confidence);
  if (pct >= 85) return "Strong";
  if (pct >= 60) return "Probable";
  if (pct >= 25) return "Possible";
  return "Unknown";
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        detail = body.detail
          .map((item: { msg?: string }) => item?.msg || JSON.stringify(item))
          .join("; ");
      } else if (body?.answer) {
        detail = body.answer;
      }
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type CaseStatus = {
  case_id: string;
  status: string;
  progress: number;
  current_stage: string;
  error?: string | null;
};

export type WalletIngestionResult = {
  case_id: string;
  wallet_address: string;
  chain: string;
  stored_transactions: number;
  transaction_count: number;
  max_hops?: number;
  wallets_ingested?: number;
  seed_wallet?: boolean;
  truncated?: boolean;
  hop_errors?: { wallet: string; error: string; hop: string }[];
  provider_empty?: boolean;
  status?: string;
  progress?: number;
};

export type AnalyzeResult = {
  graph?: Graph;
  risk?: RiskAssessment;
  attributions?: Attribution[];
  evidence?: EvidenceItem[];
  alerts?: InvestigationAlert[];
  advanced_indicators?: AdvancedIndicators;
  status?: CaseStatus;
};

export const api = {
  health: () => request<HealthStatus>("/health"),
  status: (caseId: string) => request<CaseStatus>(`/cases/${caseId}/status`),
  wallets: (caseId: string, walletAddress: string, chain = "ethereum", maxHops = 1) =>
    request<WalletIngestionResult>(`/cases/${caseId}/wallets`, {
      method: "POST",
      body: JSON.stringify({
        wallet_address: walletAddress,
        chain,
        max_hops: maxHops,
        investigation_depth: maxHops,
      }),
    }),
  caseWallets: (caseId: string) => request<CaseWallet[]>(`/cases/${caseId}/wallets`),
  transactions: (caseId: string) =>
    request<Transaction[]>(`/cases/${caseId}/transactions`),
  graph: (caseId: string) => request<Graph>(`/cases/${caseId}/graph`),
  paths: (caseId: string, wallet: string) =>
    request<Path[]>(
      `/cases/${caseId}/paths?start_wallet=${encodeURIComponent(wallet)}`,
    ),
  attributions: (caseId: string) =>
    request<Attribution[]>(`/cases/${caseId}/attributions`),
  risk: (caseId: string) => request<RiskAssessment>(`/cases/${caseId}/risk`),
  analyze: (caseId: string) =>
    request<AnalyzeResult>(`/cases/${caseId}/analyze`, { method: "POST" }),
  evidence: (caseId: string) => request<EvidenceItem[]>(`/cases/${caseId}/evidence`),
  alerts: (caseId: string) => request<InvestigationAlert[]>(`/cases/${caseId}/alerts`),
  advancedIndicators: (caseId: string) =>
    request<AdvancedIndicators>(`/cases/${caseId}/advanced-indicators`),
  crossChain: (caseId: string) =>
    request<CrossChainMovement[]>(`/cases/${caseId}/cross-chain`),
  downloadReport: async (caseId: string) => {
    const response = await fetch(`${apiBase}/cases/${caseId}/report`, { method: "POST" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `chainguard-${caseId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
  ai: {
    summary: (caseId: string) =>
      request<AIResponse>(`/cases/${caseId}/ai/summary`, { method: "POST" }),
    path: (caseId: string, pathRank?: number) =>
      request<AIResponse>(`/cases/${caseId}/ai/explain-path`, {
        method: "POST",
        body: JSON.stringify(pathRank ? { path_rank: pathRank } : {}),
      }),
    risk: (caseId: string) =>
      request<AIResponse>(`/cases/${caseId}/ai/explain-risk`, {
        method: "POST",
      }),
    attribution: (caseId: string, wallet?: string) =>
      request<AIResponse>(`/cases/${caseId}/ai/explain-attribution`, {
        method: "POST",
        body: JSON.stringify(wallet ? { wallet } : {}),
      }),
    nextSteps: (caseId: string) =>
      request<AIResponse>(`/cases/${caseId}/ai/next-steps`, { method: "POST" }),
    ask: (caseId: string, question: string) =>
      request<AIResponse>(`/cases/${caseId}/ai/ask`, {
        method: "POST",
        body: JSON.stringify({ question }),
      }),
  },
};
