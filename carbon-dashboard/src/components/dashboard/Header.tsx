import { Zap, Server, MapPin } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  metrics: any;
  zone: string;
  actionName: string;
  threshold: number;
  isLive: boolean;
  isFetching: boolean;
  dataUpdatedAt: number;
}

function formatRelative(dataUpdatedAt: number): string {
  if (!dataUpdatedAt) return "—";
  const diffMs = Date.now() - dataUpdatedAt;
  const sec = Math.floor(diffMs / 1000);
  if (sec < 1) return "just now";
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  return `${hr}h ago`;
}

export function Header({
  zone,
  actionName,
  threshold,
  isLive,
  isFetching,
  dataUpdatedAt,
}: HeaderProps) {
  const dotColor = isLive ? "bg-primary" : "bg-destructive";
  const badgeText = isLive ? (isFetching ? "SYNCING" : "LIVE") : "OFFLINE";
  const badgeClasses = isLive
    ? "bg-primary/10 text-primary border-primary/20"
    : "bg-destructive/10 text-destructive border-destructive/20";

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-border/40 gap-4"
    >
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="relative flex h-3 w-3">
            {isLive && (
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${dotColor} opacity-75`}></span>
            )}
            <span className={`relative inline-flex rounded-full h-3 w-3 ${dotColor}`}></span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight font-mono text-primary-foreground">
            Carbon-Aware Scheduler
          </h1>
          <Badge variant="outline" className={`${badgeClasses} font-mono`}>
            {badgeText}
          </Badge>
        </div>
        <p className="text-muted-foreground text-sm max-w-2xl">
          {isLive
            ? `Streaming scheduler decisions from your backend. Last update: ${formatRelative(dataUpdatedAt)}.`
            : "System actively monitoring grid intensity to defer serverless workloads during high-carbon windows."}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm bg-card/50 p-3 rounded-lg border border-border/50">
        <div className="flex items-center gap-2 px-2">
          <Server className="w-4 h-4 text-muted-foreground" />
          <span className="font-mono text-foreground">{actionName}</span>
        </div>
        <div className="w-px h-4 bg-border/50"></div>
        <div className="flex items-center gap-2 px-2">
          <MapPin className="w-4 h-4 text-muted-foreground" />
          <span className="font-mono text-foreground">{zone}</span>
        </div>
        <div className="w-px h-4 bg-border/50"></div>
        <div className="flex items-center gap-2 px-2">
          <Zap className="w-4 h-4 text-amber-500" />
          <span className="font-mono text-foreground">Thresh: {threshold}g</span>
        </div>
      </div>
    </motion.header>
  );
}
