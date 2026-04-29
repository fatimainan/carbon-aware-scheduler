import { useQuery } from "@tanstack/react-query";
import { fetchDashboardPayload } from "@/lib/api";
import type { DashboardPayload } from "@/data/simulationResults";

const REFRESH_INTERVAL_MS = 5_000;

export function useDashboardData() {
  return useQuery<DashboardPayload, Error>({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => fetchDashboardPayload(signal),
    refetchInterval: REFRESH_INTERVAL_MS,
    refetchOnWindowFocus: true,
    staleTime: 1_000,
    retry: 1,
  });
}
