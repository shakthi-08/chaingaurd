import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { deriveSummary } from "./App";
import { Sidebar } from "./components/Layout";
import { api } from "./api";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return { ...actual, api: { ...actual.api, health: vi.fn() } };
});

const roots: Root[] = [];

async function render(element: React.ReactNode): Promise<HTMLElement> {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  roots.push(root);
  await act(async () => {
    root.render(element);
  });
  return container;
}

beforeEach(() => {
  window.localStorage.clear();
  vi.mocked(api.health).mockReset();
});

afterEach(() => {
  for (const root of roots.splice(0)) {
    act(() => root.unmount());
  }
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

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
      3,
    );
    expect(summary).toEqual({
      transactions: 1,
      wallets: 2,
      hops: 1,
      importantPaths: 0,
      score: 30,
      attribution: 84,
      potentialVASPs: 1,
      suspiciousEntities: 1,
      evidenceItems: 3,
    });
  });

});

describe("dashboard connectivity indicators", () => {
  it("shows backend Online when the health request succeeds and live events Idle without a case", async () => {
    vi.mocked(api.health).mockResolvedValue({ status: "ok" });

    const view = await render(React.createElement(App));

    expect(view.textContent).toContain("Backend Online");
    expect(view.textContent).toContain("Live events idle");
    expect(view.textContent).not.toContain("Offline");
  });

  it("shows backend Offline only when the health request fails", async () => {
    vi.mocked(api.health).mockRejectedValue(new Error("health unavailable"));

    const view = await render(React.createElement(App));

    expect(view.textContent).toContain("Backend Offline");
    expect(view.textContent).toContain("Live events idle");
  });

  it("labels disabled live events independently from backend health", async () => {
    const view = await render(
      React.createElement(Sidebar, {
        activeNav: "overview",
        onNavChange: () => undefined,
        backendHealthStatus: "online",
        liveEventsStatus: "disabled",
      }),
    );

    expect(view.textContent).toContain("Backend Online");
    expect(view.textContent).toContain("Live events disabled");
  });

  it("labels a disconnected active WebSocket without marking a healthy backend Offline", async () => {
    const sockets: Array<{
      onerror: ((event: Event) => void) | null;
      onopen: (() => void) | null;
      onmessage: ((event: MessageEvent) => void) | null;
      onclose: (() => void) | null;
      close: () => void;
    }> = [];
    class MockWebSocket {
      onerror: ((event: Event) => void) | null = null;
      onopen: (() => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onclose: (() => void) | null = null;
      constructor() {
        sockets.push(this);
      }
      close() {}
    }
    vi.stubGlobal("WebSocket", MockWebSocket);
    window.localStorage.setItem(
      "chaingaurd.active-investigation",
      JSON.stringify({ caseId: "CASE-WS-1", walletAddress: "" }),
    );
    vi.mocked(api.health).mockResolvedValue({ status: "ok" });

    const view = await render(React.createElement(App));
    await act(async () => {
      sockets.at(-1)?.onerror?.(new Event("error"));
    });

    expect(view.textContent).toContain("Backend Online");
    expect(view.textContent).toContain("Live events disconnected");
    expect(view.textContent).not.toContain("Backend Offline");
  });
});
