import { Terminal } from "lucide-react";

interface FooterProps {
  actionName: string;
  zone: string;
  threshold: number;
  delaySeconds: number;
}

export function Footer({ actionName, zone, threshold, delaySeconds }: FooterProps) {
  return (
    <footer className="mt-8 pt-6 border-t border-border/40 text-xs font-mono text-muted-foreground/60 flex flex-col md:flex-row items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <Terminal className="w-4 h-4" />
        <span>Research Build v0.1.4</span>
      </div>
      <div className="flex gap-4">
        <span>ACTION_TARGET="{actionName}"</span>
        <span className="hidden md:inline">•</span>
        <span>ZONE_AFFINITY="{zone}"</span>
        <span className="hidden md:inline">•</span>
        <span>CARBON_THRESH={threshold}</span>
        <span className="hidden md:inline">•</span>
        <span>DELAY_TICK={delaySeconds}s</span>
      </div>
    </footer>
  );
}
