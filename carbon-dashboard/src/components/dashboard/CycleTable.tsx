import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { CycleResult } from "@/data/simulationResults";
import { CheckCircle2, Timer } from "lucide-react";
import { motion } from "framer-motion";

interface CycleTableProps {
  cycles: CycleResult[];
}

export function CycleTable({ cycles }: CycleTableProps) {
  return (
    <div className="rounded-lg border border-border/50 bg-card/40 overflow-hidden">
      <div className="p-4 border-b border-border/50 bg-card/60 flex items-center justify-between">
        <h3 className="font-mono text-sm font-medium text-muted-foreground">Execution Log</h3>
        <span className="font-mono text-xs text-muted-foreground/70">
          {cycles.length} {cycles.length === 1 ? "cycle" : "cycles"}
        </span>
      </div>
      <Table>
        <TableHeader className="bg-card/40">
          <TableRow className="hover:bg-transparent border-border/50">
            <TableHead className="w-[80px] font-mono text-xs">Cycle</TableHead>
            <TableHead className="font-mono text-xs">Time Offset</TableHead>
            <TableHead className="font-mono text-xs">Intensity</TableHead>
            <TableHead className="font-mono text-xs">Decision</TableHead>
            <TableHead className="font-mono text-xs">Status</TableHead>
            <TableHead className="text-right font-mono text-xs">Duration</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cycles.length === 0 && (
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableCell
                colSpan={6}
                className="text-center text-muted-foreground/70 font-mono text-xs py-10"
              >
                No cycles recorded yet.
              </TableCell>
            </TableRow>
          )}
          {cycles.map((cycle, index) => (
            <TableRow 
              key={cycle.cycle}
              className="border-border/50 hover:bg-muted/30 transition-colors"
            >
              <TableCell className="font-mono text-xs text-muted-foreground">
                #{cycle.cycle.toString().padStart(2, '0')}
              </TableCell>
              <TableCell className="font-mono text-sm">
                T+{cycle.timestampOffsetMin}m
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <div 
                    className={`w-2 h-2 rounded-full ${
                      cycle.decision === 'execute' ? 'bg-primary' : 'bg-destructive'
                    }`} 
                  />
                  <span className="font-mono text-sm">{cycle.carbonIntensity} <span className="text-xs text-muted-foreground">gCO₂</span></span>
                </div>
              </TableCell>
              <TableCell>
                <Badge 
                  variant="outline" 
                  className={`font-mono text-xs ${
                    cycle.decision === 'execute' 
                      ? 'bg-primary/10 text-primary border-primary/20' 
                      : 'bg-amber-500/10 text-amber-500 border-amber-500/20'
                  }`}
                >
                  {cycle.decision.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground">
                  {cycle.executionStatus === 'executed' ? (
                    <><CheckCircle2 className="w-3.5 h-3.5 text-primary/80" /> Executed</>
                  ) : (
                    <><Timer className="w-3.5 h-3.5 text-amber-500/80" /> Delayed</>
                  )}
                </div>
              </TableCell>
              <TableCell className="text-right font-mono text-sm text-muted-foreground">
                {cycle.executionDurationMs !== null 
                  ? `${cycle.executionDurationMs.toFixed(2)}ms` 
                  : <span className="text-amber-500/70">--</span>}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
