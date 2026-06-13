import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, Scatter, LabelList } from "recharts";
import { CycleResult } from "@/data/simulationResults";

interface PrimaryChartProps {
  cycles: CycleResult[];
  threshold: number;
}

export function PrimaryChart({ cycles, threshold }: PrimaryChartProps) {
  const formatLabel = (c: CycleResult) => {
    if (c.taskName) {
      return c.taskName.replace("Request #", "Req #");
    }
    return `Req #${c.cycle}`;
  };

  const chartData = cycles.map(c => ({
    time: c.timestampOffsetMin,
    carbon: c.carbonIntensity,
    decision: c.decision,
    label: formatLabel(c),
    isDelayed: c.decision === "delay" ? c.carbonIntensity : null,
    isExecuted: c.decision === "execute" ? c.carbonIntensity : null
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-card/95 border border-border p-3 rounded-lg shadow-xl backdrop-blur-md font-mono text-sm">
          <p className="text-muted-foreground mb-2">T+{data.time} min</p>
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">Intensity:</span>
              <span className="font-bold text-foreground">{data.carbon} gCO₂</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-muted-foreground">Action:</span>
              <span className={`font-bold ${data.decision === 'delay' ? 'text-amber-500' : 'text-primary'}`}>
                {data.decision.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="bg-card/40 border-border/50 h-full flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium font-mono flex items-center justify-between">
          <span>Grid Carbon Intensity & Scheduler Decisions</span>
          <div className="flex gap-4 text-xs font-normal">
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-primary opacity-80" /> Executed</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-amber-500 opacity-80" /> Delayed</div>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="opacity-10" vertical={false} />
            <XAxis 
              dataKey="time" 
              stroke="currentColor" 
              className="text-xs opacity-50 font-mono" 
              tickFormatter={(val) => `+${val}m`}
              tickMargin={10}
            />
            <YAxis 
              stroke="currentColor" 
              className="text-xs opacity-50 font-mono" 
              tickFormatter={(val) => `${val}g`}
              tickMargin={10}
              domain={[0, (dataMax: number) => Math.ceil(dataMax / 50) * 50]}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'var(--color-muted)', strokeWidth: 1, strokeDasharray: '4 4' }} />
            
            <ReferenceLine 
              y={threshold} 
              stroke="var(--color-destructive)" 
              strokeDasharray="4 4" 
              strokeWidth={1}
              label={{ 
                position: 'insideTopLeft', 
                value: `THRESHOLD (${threshold}g)`, 
                fill: 'var(--color-destructive)',
                fontSize: 10,
                className: 'font-mono',
                opacity: 0.8
              }} 
            />
            
            <Line 
              type="monotone" 
              dataKey="carbon" 
              stroke="var(--color-border)" 
              strokeWidth={2}
              dot={false}
              activeDot={false}
              className="opacity-40"
            />

            <Scatter dataKey="isExecuted" fill="var(--color-primary)" className="opacity-80">
              <LabelList dataKey="label" position="top" style={{ fill: '#10b981', fontSize: 10, fontFamily: 'monospace', fontWeight: 'bold' }} />
            </Scatter>
            <Scatter dataKey="isDelayed" fill="var(--color-chart-3)" className="opacity-80">
              <LabelList dataKey="label" position="top" style={{ fill: '#f59e0b', fontSize: 10, fontFamily: 'monospace', fontWeight: 'bold' }} />
            </Scatter>
            
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
