import { Header } from "@/components/dashboard/Header";
import { KPIStrip } from "@/components/dashboard/KPIStrip";
import { PrimaryChart } from "@/components/dashboard/PrimaryChart";
import { SecondaryCharts } from "@/components/dashboard/SecondaryCharts";
import { CycleTable } from "@/components/dashboard/CycleTable";
import { Footer } from "@/components/dashboard/Footer";
import { DashboardStateBanner } from "@/components/dashboard/DashboardStateBanner";
import { WorkerConsole } from "@/components/dashboard/WorkerConsole";
import {
  deriveMetrics,
  EMPTY_METRICS,
  FALLBACK_CONFIG,
} from "@/data/simulationResults";
import { useDashboardData } from "@/hooks/useDashboardData";
import { useQueryClient } from "@tanstack/react-query";
import { updateThreshold } from "@/lib/api";

export default function Dashboard() {
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error, isFetching, dataUpdatedAt } =
    useDashboardData();

  const config = data?.config ?? FALLBACK_CONFIG;
  const cycles = data?.cycles ?? [];
  const metrics = data ? deriveMetrics(cycles, config) : EMPTY_METRICS;

  const handleThresholdChange = async (newVal: number) => {
    try {
      await updateThreshold(newVal);
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err) {
      console.error("Failed to update threshold:", err);
    }
  };

  return (
    <div className="min-h-[100dvh] bg-background text-foreground font-sans selection:bg-primary/30">
      <div className="max-w-[1400px] mx-auto p-4 md:p-8 space-y-8">
        <Header
          metrics={metrics}
          zone={config.zone}
          actionName={config.actionName}
          threshold={config.threshold}
          isLive={!isError}
          isFetching={isFetching}
          dataUpdatedAt={dataUpdatedAt}
          currentCarbon={cycles.length > 0 ? cycles[cycles.length - 1].carbonIntensity : null}
          onThresholdChange={handleThresholdChange}
        />

        <DashboardStateBanner
          isLoading={isLoading}
          isError={isError}
          errorMessage={error?.message}
          isEmpty={!isLoading && !isError && cycles.length === 0}
        />

        <KPIStrip metrics={metrics} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <PrimaryChart cycles={cycles} threshold={config.threshold} />
          </div>
          <div>
            <SecondaryCharts
              metrics={metrics}
              delaySeconds={config.delaySeconds}
            />
          </div>
        </div>

        <CycleTable cycles={cycles} />

        <WorkerConsole logs={data?.workerLogs ?? []} />

        <Footer
          actionName={config.actionName}
          zone={config.zone}
          threshold={config.threshold}
          delaySeconds={config.delaySeconds}
        />
      </div>
    </div>
  );
}
