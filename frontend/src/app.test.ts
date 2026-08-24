import { describe, expect, it } from "vitest";
import { deriveSummary } from "./App";

describe("dashboard summary", () => {
  it("derives investigator metrics from backend responses", () => {
    const summary = deriveSummary(
      [
        {
          tx_hash: "tx",
          from: "a",
          to: "b",
          value: "1",
          token: "ETH",
          timestamp: "2024-01-01T00:00:00Z",
          block: 1,
        },
      ],
      {
        nodes: [
          { id: "a", type: "wallet" },
          { id: "b", type: "wallet" },
        ],
        edges: [],
        transactions: [],
      },
      [
        {
          rank: 1,
          start_wallet: "a",
          end_wallet: "b",
          wallets: ["a", "b"],
          transactions: ["tx"],
          hop_count: 1,
          total_value: "1",
          values: ["1"],
          timestamps: [],
        },
      ],
      {
        overall_score: 30,
        risk_level: "LOW",
        indicators: [],
        findings: [],
        explanations: [],
        evidence_refs: [],
      },
      [
        {
          wallet: "a",
          entity: "Demo",
          entity_id: "e",
          entity_type: "vasp",
          chain: "ethereum",
          confidence: 84,
          reasons: [],
          source: "demo",
          evidence_refs: [],
          explanation: "",
        },
      ],
    );
    expect(summary).toEqual({
      transactions: 1,
      wallets: 2,
      hops: 1,
      importantPaths: 0,
      score: 30,
      attribution: 84,
    });
  });
});
