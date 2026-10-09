export type BackendHealthStatus = "checking" | "online" | "offline";
export type LiveEventsStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "disconnected"
  | "disabled";

export function backendHealthLabel(status: BackendHealthStatus): string {
  if (status === "online") return "Backend Online";
  if (status === "offline") return "Backend Offline";
  return "Checking backend";
}

export function liveEventsLabel(status: LiveEventsStatus): string {
  if (status === "connected") return "Live events connected";
  if (status === "connecting") return "Live events connecting";
  if (status === "disconnected") return "Live events disconnected";
  if (status === "disabled") return "Live events disabled";
  return "Live events idle";
}
