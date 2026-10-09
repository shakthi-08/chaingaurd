import React, { useEffect, useState } from "react";
import { Badge, Button, Card } from "../components/BaseComponents";
import type { AIResponse } from "../api";
import "./AIInvestigation.css";

interface AIInvestigationProps {
  caseId: string;
  response?: AIResponse | null;
  health?: { ai_provider?: string; ai_configured?: boolean; ai_model?: string | null } | null;
  onAsk?: (question: string) => Promise<AIResponse | null | undefined>;
  onAction?: (
    action: "summary" | "risk" | "attribution" | "path" | "nextSteps",
  ) => Promise<AIResponse | null | undefined>;
}

export const AIInvestigation: React.FC<AIInvestigationProps> = ({
  caseId,
  response,
  health,
  onAsk,
  onAction,
}) => {
  const [question, setQuestion] = useState("");
  const [current, setCurrent] = useState<AIResponse | null>(response || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (response) setCurrent(response);
  }, [response]);

  const run = async (task: () => Promise<AIResponse | null | undefined>) => {
    setLoading(true);
    setError(null);
    try {
      const result = await task();
      if (result) setCurrent(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "AI request failed");
    } finally {
      setLoading(false);
    }
  };

  const providerStatus = String(current?.provider_status || "").toLowerCase();
  const configured = health?.ai_configured === true;
  const providerNotConfigured =
    (!configured && !current) ||
    (Boolean(current) &&
      (providerStatus === "unavailable" || providerStatus === "none"));
  const unavailable = Boolean(current) && providerStatus !== "available";

  return (
    <div className="ai-investigation">
      <Card>
        <h3>AI investigation for {caseId}</h3>
        <p>
          Answers are generated from current case context (wallets, transactions, graph, risk, attribution, evidence).
          No canned responses are used. Deterministic ChainGuard analysis remains independent of AI.
        </p>
        {(providerNotConfigured || health?.ai_configured === false) && (
          <p>
            AI provider is not configured
            {health?.ai_provider ? ` (AI_PROVIDER=${health.ai_provider})` : ""}.
            Set <code>AI_PROVIDER=openai</code> and <code>AI_API_KEY</code> in{" "}
            <code>backend/.env</code> (optional <code>AI_MODEL=gpt-4o-mini</code>),
            or use <code>AI_PROVIDER=ollama</code> with a local model, then restart the backend.
          </p>
        )}
        {configured && health?.ai_model && (
          <p>
            Configured provider: {health.ai_provider} · model {health.ai_model}
          </p>
        )}
        <div className="ai-investigation__findings-grid">
          <Button variant="secondary" size="sm" disabled={loading} onClick={() => run(async () => onAction?.("summary") ?? null)}>
            Case summary
          </Button>
          <Button variant="secondary" size="sm" disabled={loading} onClick={() => run(async () => onAction?.("risk") ?? null)}>
            Why is this risky?
          </Button>
          <Button variant="secondary" size="sm" disabled={loading} onClick={() => run(async () => onAction?.("attribution") ?? null)}>
            Explain attribution
          </Button>
          <Button variant="secondary" size="sm" disabled={loading} onClick={() => run(async () => onAction?.("path") ?? null)}>
            Explain suspicious flow
          </Button>
          <Button variant="secondary" size="sm" disabled={loading} onClick={() => run(async () => onAction?.("nextSteps") ?? null)}>
            Investigator next steps
          </Button>
        </div>
        <div className="new-investigation__field" style={{ marginTop: 16 }}>
          <label htmlFor="ai-question">Ask a question about this case</label>
          <input
            id="ai-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && question.trim()) {
                void run(async () => onAsk?.(question.trim()) ?? null);
              }
            }}
            placeholder="e.g. Which hop concentrates value toward an exchange?"
          />
          <Button
            disabled={loading || !question.trim()}
            onClick={() => run(async () => onAsk?.(question.trim()) ?? null)}
          >
            Ask
          </Button>
        </div>
      </Card>

      {error && <Card><p>{error}</p></Card>}
      {loading && <Card><p>Requesting AI analysis for the current case…</p></Card>}

      {current && (
        <Card>
          <div>
            <Badge variant={current.provider_status === "available" ? "success" : "warning"}>
              {current.provider_status}
            </Badge>
            {current.model && <span> · {current.model}</span>}
            <span> · {current.provider}</span>
          </div>
          {providerNotConfigured && (
            <p>
              AI provider is not configured.
              {current.answer ? ` ${current.answer}` : ""}
            </p>
          )}
          {unavailable && !providerNotConfigured && (
            <p>
              {current.answer ||
                "AI assistance is unavailable because no provider is configured, or the provider could not be reached."}
            </p>
          )}
          {!unavailable && <p>{current.answer}</p>}
          {current.limitations?.length > 0 && (
            <ul>
              {current.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          {current.evidence_refs?.length > 0 && (
            <p>Evidence refs: {current.evidence_refs.join(", ")}</p>
          )}
        </Card>
      )}
    </div>
  );
};
