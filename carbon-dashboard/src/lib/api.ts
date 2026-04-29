import type { DashboardPayload } from "@/data/simulationResults";

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
export const API_BASE_URL = RAW_BASE_URL.replace(/\/$/, "");

export const DASHBOARD_ENDPOINT = `${API_BASE_URL}/api/dashboard`;

export async function fetchDashboardPayload(
  signal?: AbortSignal,
): Promise<DashboardPayload> {
  const res = await fetch(DASHBOARD_ENDPOINT, {
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
