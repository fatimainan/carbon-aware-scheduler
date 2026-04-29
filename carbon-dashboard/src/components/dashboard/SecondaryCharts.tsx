import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, Cell, PieChart, Pie, Cell as PieCell } from "recharts";
import { Badge } from "@/components/ui/badge";

interface SecondaryChartsProps {
  metrics: any;
  delaySeconds: number;
}

export function SecondaryCharts({ metrics, delaySeconds }: SecondaryChartsProps) {
  const avgCarbonData = [
    { name: "Exec", value: metrics.avgCarbonOnExecute, fill: "var(--color-primary)" },
    { name: "Delay", value: metrics.avgCarbonOnDelay, fill: "var(--color-chart-3)" }
  ];

  const distributionData = [
    { name: "Executed", value: metrics.executedCount, color: "var(--color-primary)" },
    { name: "Delayed", value: metrics.delayedCount, color: "var(--color-chart-3)" }
  ];

  return (
    <div className="flex flex-col gap-6 h-full">
      <Card className="bg-card/40 border-border/50 flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium font-mono text-muted-foreground">
            Carbon Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end justify-between mb-4">
            <div>
              <p className="text-2xl font-mono font-bold text-primary">{metrics.avgCarbonOnExecute.toFixed(0)}g</p>
              <p className="text-xs text-muted-foreground">Avg when executed</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-mono font-bold text-amber-500">{metrics.avgCarbonOnDelay.toFixed(0)}g</p>
              <p className="text-xs text-muted-foreground">Avg when delayed</p>
            </div>
          </div>
          <div className="h-[80px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={avgCarbonData} layout="vertical" margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" hide />
                <RechartsTooltip 
                  cursor={{fill: 'transparent'}}
                  content={({active, payload}) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-card border border-border p-2 rounded text-xs font-mono">
                          {payload[0].payload.name}: {Number(payload[0].value).toFixed(1)}g
                        </div>
                      )
                    }
                    return null;
                  }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
                  {avgCarbonData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} className="opacity-80 hover:opacity-100 transition-opacity" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-card/40 border-border/50 flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium font-mono text-muted-foreground">
            Decision Distribution
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div className="h-[100px] w-[100px]">
             <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={distributionData}
                  innerRadius={30}
                  outerRadius={45}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {distributionData.map((entry, index) => (
                    <PieCell key={`cell-${index}`} fill={entry.color} className="opacity-80 hover:opacity-100 transition-opacity" />
                  ))}
                </Pie>
                <RechartsTooltip 
                  content={({active, payload}) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-card border border-border p-2 rounded text-xs font-mono">
                          {payload[0].payload.name}: {payload[0].value}
                        </div>
                      )
                    }
                    return null;
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2 text-right">
            <div>
              <p className="text-xl font-mono font-bold text-primary">{metrics.executedPercent.toFixed(0)}%</p>
              <p className="text-xs text-muted-foreground">Executed</p>
            </div>
            <div>
              <p className="text-xl font-mono font-bold text-amber-500">{metrics.delayedPercent.toFixed(0)}%</p>
              <p className="text-xs text-muted-foreground">Delayed</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-card/40 border-border/50 flex-1">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium font-mono text-muted-foreground">
            Latency Impact
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1 font-mono">
                <span className="text-muted-foreground">Baseline (Immediate)</span>
                <span className="text-foreground">{metrics.baselineLatencyMs.toFixed(1)}ms</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                <div className="bg-muted-foreground/40 h-full w-[2%]" />
              </div>
            </div>
            
            <div>
              <div className="flex justify-between text-xs mb-1 font-mono">
                <span className="text-muted-foreground">Carbon-Aware</span>
                <span className="text-amber-500 font-bold">{(metrics.carbonAwareLatencyMs / 1000).toFixed(1)}s</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 overflow-hidden flex">
                <div className="bg-primary/50 h-full w-[2%]" title="Execution Time" />
                <div className="bg-amber-500/80 h-full w-[98%]" title="Delay Time" />
              </div>
            </div>
            
            <div className="pt-2">
               <Badge variant="outline" className="text-xs bg-amber-500/10 text-amber-500 border-amber-500/20 font-mono w-full justify-center">
                 Configured Delay: {delaySeconds}s
               </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
