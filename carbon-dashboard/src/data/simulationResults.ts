export interface CycleResult {
  cycle: number;
  timestampOffsetMin: number;
  carbonIntensity: number;
  threshold: number;
  decision: "execute" | "delay";
  executionStatus: "executed" | "delayed" | "queued";
  executionDurationMs: number | null;
  scenario: "A" | "B";
  taskName?: string;
}

export interface RunConfig {
  threshold: number;
  delaySeconds: number;
  zone: string;
  actionName: string;
}

export interface DashboardPayload {
  config: RunConfig;
  cycles: CycleResult[];
  workerLogs: string[];
  generatedAt: string;
}

export interface DerivedMetrics {
  totalCycles: number;
  executedCount: number;
  delayedCount: number;
  executedPercent: number;
  delayedPercent: number;
  avgCarbonIntensity: number;
  minCarbon: number;
  maxCarbon: number;
  medianCarbon: number;
  avgCarbonOnExecute: number;
  avgCarbonOnDelay: number;
  carbonSavedGCO2: number;
  percentReduction: number;
  baselineLatencyMs: number;
  carbonAwareLatencyMs: number;
  latencyOverheadMs: number;
  latencyOverheadFactor: number;
  tradeoffRatio: number;
}

export const EMPTY_METRICS: DerivedMetrics = {
  totalCycles: 0,
  executedCount: 0,
  delayedCount: 0,
  executedPercent: 0,
  delayedPercent: 0,
  avgCarbonIntensity: 0,
  minCarbon: 0,
  maxCarbon: 0,
  medianCarbon: 0,
  avgCarbonOnExecute: 0,
  avgCarbonOnDelay: 0,
  carbonSavedGCO2: 0,
  percentReduction: 0,
  baselineLatencyMs: 0,
  carbonAwareLatencyMs: 0,
  latencyOverheadMs: 0,
  latencyOverheadFactor: 0,
  tradeoffRatio: 0,
};

export function deriveMetrics(
  cycles: CycleResult[],
  config: RunConfig,
): DerivedMetrics {
  const totalCycles = cycles.length;
  if (totalCycles === 0) return EMPTY_METRICS;

  const executedCycles = cycles.filter((c) => c.decision === "execute");
  const delayedCycles = cycles.filter((c) => c.decision === "delay");

  const executedCount = executedCycles.length;
  const delayedCount = delayedCycles.length;

  const executedPercent = (executedCount / totalCycles) * 100;
  const delayedPercent = (delayedCount / totalCycles) * 100;

  const carbonIntensities = cycles.map((c) => c.carbonIntensity);
  const avgCarbonIntensity =
    carbonIntensities.reduce((a, b) => a + b, 0) / totalCycles;
  const minCarbon = Math.min(...carbonIntensities);
  const maxCarbon = Math.max(...carbonIntensities);
  const sortedCarbon = [...carbonIntensities].sort((a, b) => a - b);
  const medianCarbon = sortedCarbon[Math.floor(sortedCarbon.length / 2)] ?? 0;

  const avgCarbonOnExecute =
    executedCount > 0
      ? executedCycles.reduce((sum, c) => sum + c.carbonIntensity, 0) /
        executedCount
      : 0;
  const avgCarbonOnDelay =
    delayedCount > 0
      ? delayedCycles.reduce((sum, c) => sum + c.carbonIntensity, 0) /
        delayedCount
      : 0;

  const carbonSavedGCO2 = delayedCycles.reduce(
    (sum, c) => sum + (c.carbonIntensity - c.threshold),
    0,
  );
  const baselineTotalCarbon = carbonIntensities.reduce((sum, c) => sum + c, 0);
  const percentReduction =
    baselineTotalCarbon > 0
      ? (carbonSavedGCO2 / baselineTotalCarbon) * 100
      : 0;

  const avgExecuteDuration =
    executedCount > 0
      ? executedCycles.reduce((sum, c) => sum + (c.executionDurationMs || 0), 0) /
        executedCount
      : 0;

  const baselineLatencyMs = totalCycles * avgExecuteDuration;

  const executedLatencyTotal = executedCycles.reduce(
    (sum, c) => sum + (c.executionDurationMs || 0),
    0,
  );
  const delayedLatencyTotal = delayedCount * (config.delaySeconds * 1000);
  const carbonAwareLatencyMs = executedLatencyTotal + delayedLatencyTotal;

  const latencyOverheadMs = carbonAwareLatencyMs - baselineLatencyMs;
  const latencyOverheadFactor =
    baselineLatencyMs > 0 ? carbonAwareLatencyMs / baselineLatencyMs : 0;

  const tradeoffRatio =
    latencyOverheadMs > 0 ? carbonSavedGCO2 / (latencyOverheadMs / 1000) : 0;

  return {
    totalCycles,
    executedCount,
    delayedCount,
    executedPercent,
    delayedPercent,
    avgCarbonIntensity,
    minCarbon,
    maxCarbon,
    medianCarbon,
    avgCarbonOnExecute,
    avgCarbonOnDelay,
    carbonSavedGCO2,
    percentReduction,
    baselineLatencyMs,
    carbonAwareLatencyMs,
    latencyOverheadMs,
    latencyOverheadFactor,
    tradeoffRatio,
  };
}

export const FALLBACK_CONFIG: RunConfig = {
  threshold: 200,
  delaySeconds: 30,
  zone: "DE",
  actionName: "data_processor",
};

export const FALLBACK_CYCLES: CycleResult[] = [
  { cycle: 1,  timestampOffsetMin: 0,  carbonIntensity: 85,  threshold: 200, decision: "execute", executionStatus: "executed", executionDurationMs: 0.31, scenario: "A" },
  { cycle: 2,  timestampOffsetMin: 5,  carbonIntensity: 110, threshold: 200, decision: "execute", executionStatus: "executed", executionDurationMs: 0.17, scenario: "A" },
  { cycle: 3,  timestampOffsetMin: 10, carbonIntensity: 160, threshold: 200, decision: "execute", executionStatus: "executed", executionDurationMs: 0.17, scenario: "A" },
  { cycle: 4,  timestampOffsetMin: 15, carbonIntensity: 210, threshold: 200, decision: "delay",   executionStatus: "delayed",  executionDurationMs: null, scenario: "B" },
  { cycle: 5,  timestampOffsetMin: 20, carbonIntensity: 275, threshold: 200, decision: "delay",   executionStatus: "delayed",  executionDurationMs: null, scenario: "B" },
  { cycle: 6,  timestampOffsetMin: 25, carbonIntensity: 320, threshold: 200, decision: "delay",   executionStatus: "delayed",  executionDurationMs: null, scenario: "B" },
  { cycle: 7,  timestampOffsetMin: 30, carbonIntensity: 180, threshold: 200, decision: "execute", executionStatus: "executed", executionDurationMs: 0.19, scenario: "A" },
  { cycle: 8,  timestampOffsetMin: 35, carbonIntensity: 95,  threshold: 200, decision: "execute", executionStatus: "executed", executionDurationMs: 0.16, scenario: "A" },
  { cycle: 9,  timestampOffsetMin: 40, carbonIntensity: 240, threshold: 200, decision: "delay",   executionStatus: "delayed",  executionDurationMs: null, scenario: "B" },
  { cycle: 10, timestampOffsetMin: 45, carbonIntensity: 130, threshold: 200, decision: "execute", executionStatus: "executed", executionDurationMs: 0.16, scenario: "A" },
];
