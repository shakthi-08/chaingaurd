export type Transaction = {
  tx_hash: string;
  from: string;
  to: string;
  value: string;
  token: string | null;
  timestamp: string;
  block: number | null;
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
};
export type Graph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  transactions: GraphEdge[];
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
};

const apiBase = import.meta.env.VITE_API_BASE ?? "/api";

export function realtimeUrl(caseId: string): string {
  const configured = import.meta.env.VITE_WS_BASE;
  if (configured) return `${configured}/cases/${caseId}/events`;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/cases/${caseId}/events`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok)
    throw new Error(`${response.status} ${response.statusText}`);
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
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
    request<RiskAssessment>(`/cases/${caseId}/analyze`, { method: "POST" }),
  crossChain: (caseId: string) =>
    request<CrossChainMovement[]>(`/cases/${caseId}/cross-chain`),
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
  },
};
