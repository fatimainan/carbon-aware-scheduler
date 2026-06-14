import type { DashboardPayload } from "@/data/simulationResults";

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
export const API_BASE_URL = RAW_BASE_URL.replace(/\/$/, "");

export const DASHBOARD_ENDPOINT = `${API_BASE_URL}/api/dashboard`;

export async function fetchDashboardPayload(
  signal?: AbortSignal,
): Promise<DashboardPayload> {
  const urlParams = new URLSearchParams(window.location.search);
  const mode = urlParams.get("mode") || "sandbox";

  const res = await fetch(`${DASHBOARD_ENDPOINT}?mode=${mode}`, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(
      `Failed to fetch dashboard data: ${res.status} ${res.statusText}`,
    );
  }

  const data = (await res.json()) as DashboardPayload;

  if (!data || !Array.isArray(data.cycles) || !data.config) {
    throw new Error("Invalid dashboard payload shape");
  }

  return data;
}

export async function updateThreshold(newThreshold: number): Promise<void> {
  const urlParams = new URLSearchParams(window.location.search);
  const mode = urlParams.get("mode") || "sandbox";

  const res = await fetch(`${API_BASE_URL}/api/threshold?mode=${mode}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ threshold: newThreshold }),
  });

  if (!res.ok) {
    throw new Error(
      `Failed to update threshold: ${res.status} ${res.statusText}`,
    );
  }
}
