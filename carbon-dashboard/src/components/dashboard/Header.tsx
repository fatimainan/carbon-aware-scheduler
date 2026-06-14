import { Zap, Server, MapPin, Pencil, Check, X } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { useState, useEffect } from "react";

interface HeaderProps {
  metrics: any;
  zone: string;
  actionName: string;
  threshold: number;
  isLive: boolean;
  isFetching: boolean;
  dataUpdatedAt: number;
  currentCarbon: number | null;
  onThresholdChange?: (val: number) => Promise<void>;
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
  currentCarbon,
  onThresholdChange,
}: HeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [tempValue, setTempValue] = useState(String(threshold));

  useEffect(() => {
    setTempValue(String(threshold));
  }, [threshold]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const val = parseFloat(tempValue);
    if (!isNaN(val) && val >= 0) {
      if (onThresholdChange) {
        try {
          await onThresholdChange(val);
        } catch (err) {
          console.error(err);
        }
      }
      setIsEditing(false);
    }
  };

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

      <div className="flex flex-wrap items-center gap-4">
        {currentCarbon !== null && (
          <div className="flex flex-col items-start md:items-end justify-center px-4 py-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20 shadow-md">
            <span className="text-[10px] text-emerald-400/80 uppercase font-mono tracking-widest font-bold">CURRENT CARBON</span>
            <span className="text-2xl md:text-3xl font-extrabold font-mono leading-none mt-1">
              {currentCarbon} <span className="text-xs font-normal text-muted-foreground font-sans">gCO₂/kWh</span>
            </span>
          </div>
        )}

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
            {isEditing ? (
              <form onSubmit={handleSave} className="flex items-center gap-1.5">
                <span className="font-mono text-muted-foreground text-xs">Thresh:</span>
                <input
                  type="number"
                  value={tempValue}
                  onChange={(e) => setTempValue(e.target.value)}
                  className="w-16 bg-muted/80 text-foreground border border-border/50 rounded px-1.5 py-0.5 text-xs font-mono text-center focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/25"
                  autoFocus
                />
                <button type="submit" className="text-emerald-500 hover:text-emerald-400 p-0.5 transition-colors" title="Save">
                  <Check className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setTempValue(String(threshold));
                    setIsEditing(false);
                  }}
                  className="text-destructive hover:text-destructive/80 p-0.5 transition-colors"
                  title="Cancel"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </form>
            ) : (
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-1 font-mono text-foreground hover:text-amber-500 transition-colors focus:outline-none group"
                title="Click to edit threshold"
              >
                <span>Thresh: {threshold}g</span>
                <Pencil className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity ml-0.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </motion.header>
  );
}
