import { motion, type Variants } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Leaf, Clock, ArrowDownRight, ActivitySquare } from "lucide-react";

interface KPIStripProps {
  metrics: any;
}

export function KPIStrip({ metrics }: KPIStripProps) {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const item: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
    >
      <motion.div variants={item}>
        <Card className="bg-card/40 backdrop-blur-sm border-border/50 overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Leaf className="w-16 h-16 text-primary" />
          </div>
          <CardContent className="p-6">
            <p className="text-sm font-medium text-muted-foreground mb-1">Carbon Saved</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-4xl font-bold tracking-tighter text-primary font-mono">
                {metrics.carbonSavedGCO2.toFixed(1)}
              </h3>
              <span className="text-sm text-muted-foreground font-mono">gCO₂/kWh</span>
            </div>
            <p className="text-xs text-primary/80 mt-2 flex items-center gap-1">
              <ArrowDownRight className="w-3 h-3" />
              {metrics.percentReduction.toFixed(1)}% vs baseline avg
            </p>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card className="bg-card/40 backdrop-blur-sm border-border/50 overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Clock className="w-16 h-16 text-amber-500" />
          </div>
          <CardContent className="p-6">
            <p className="text-sm font-medium text-muted-foreground mb-1">Latency Overhead</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-4xl font-bold tracking-tighter text-amber-500 font-mono">
                {(metrics.latencyOverheadMs / 1000).toFixed(0)}
              </h3>
              <span className="text-sm text-muted-foreground font-mono">s</span>
            </div>
            <p className="text-xs text-amber-500/80 mt-2">
              ≈ {(metrics.latencyOverheadFactor).toFixed(0)}× baseline duration
            </p>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card className="bg-card/40 backdrop-blur-sm border-border/50 overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <ActivitySquare className="w-16 h-16 text-blue-500" />
          </div>
          <CardContent className="p-6">
            <p className="text-sm font-medium text-muted-foreground mb-1">Tradeoff Ratio</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-4xl font-bold tracking-tighter text-blue-400 font-mono">
                {metrics.tradeoffRatio.toFixed(2)}
              </h3>
            </div>
            <p className="text-xs text-blue-400/80 mt-2">
              gCO₂ saved per sec of latency
            </p>
          </CardContent>
        </Card>
      </motion.div>

      <motion.div variants={item}>
        <Card className="bg-card/40 backdrop-blur-sm border-border/50 overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <div className="text-6xl font-black text-foreground">!</div>
          </div>
          <CardContent className="p-6">
            <p className="text-sm font-medium text-muted-foreground mb-1">Workloads Deferred</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-4xl font-bold tracking-tighter text-foreground font-mono">
                {metrics.delayedPercent.toFixed(0)}%
              </h3>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {metrics.delayedCount} of {metrics.totalCycles} cycles delayed
            </p>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  );
}
