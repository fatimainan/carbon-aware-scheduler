import { useEffect, useRef } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Terminal } from "lucide-react";

interface WorkerConsoleProps {
  logs: string[];
}

export function WorkerConsole({ logs }: WorkerConsoleProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll container to bottom when new logs arrive (without scrolling the viewport)
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  // Parse log lines to apply coloring based on log level
  const formatLogLine = (line: string, index: number) => {
    let textColor = "text-zinc-300";
    if (
      line.includes("WARNING") ||
      line.includes("WARN") ||
      line.includes("delay") ||
      line.includes("Zamanı gelmedi") ||
      line.includes("bekletiliyor")
    ) {
      textColor = "text-amber-400";
    } else if (
      line.includes("ERROR") ||
      line.includes("FAIL") ||
      line.includes("hata") ||
      line.includes("başarısız")
    ) {
      textColor = "text-red-400";
    } else if (
      line.includes("EXECUTE") ||
      line.includes("success") ||
      line.includes("completed") ||
      line.includes("🟢") ||
      line.includes("Koşullar uygun") ||
      line.includes("Tamamlandı")
    ) {
      textColor = "text-emerald-400";
    } else if (
      line.includes("Processing decision") ||
      line.includes("Worker başlatıldı") ||
      line.includes("═══════════════════════")
    ) {
      textColor = "text-blue-400";
    }

    return (
      <div key={index} className={`py-0.5 leading-relaxed ${textColor}`}>
        {line}
      </div>
    );
  };

  return (
    <Card className="bg-card/40 border-border/50 overflow-hidden flex flex-col h-[300px]">
      <CardHeader className="pb-2 bg-card/60 border-b border-border/40 py-3">
        <CardTitle className="text-sm font-medium font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-blue-400 animate-pulse" />
            <span>Worker Queue Console</span>
          </div>
          <div className="flex items-center gap-2 text-xs font-normal text-muted-foreground">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-mono">Active Monitoring</span>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent ref={containerRef} className="flex-1 overflow-y-auto p-4 bg-zinc-950/80 font-mono text-xs select-text scrollbar-thin">
        {logs.length === 0 ? (
          <div className="text-zinc-500 italic text-center py-12">
            No worker logs recorded yet. Run the scheduler with --zone or --sim to populate queue events.
          </div>
        ) : (
          <div className="space-y-0.5">
            {logs.map((line, idx) => formatLogLine(line, idx))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
