import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, Loader2, Inbox } from "lucide-react";
import { DASHBOARD_ENDPOINT } from "@/lib/api";

interface Props {
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  isEmpty: boolean;
}

export function DashboardStateBanner({
  isLoading,
  isError,
  errorMessage,
  isEmpty,
}: Props) {
  const visible = isLoading || isError || isEmpty;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {isLoading && (
            <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-card/60 px-4 py-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="font-mono">
                Connecting to scheduler API…
              </span>
              <span className="ml-auto truncate font-mono text-xs opacity-60">
                {DASHBOARD_ENDPOINT}
              </span>
            </div>
          )}

          {isError && (
            <div className="flex flex-col gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm">
              <div className="flex items-center gap-3 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span className="font-semibold font-mono">
                  Cannot reach the scheduler API
                </span>
              </div>
              <p className="text-muted-foreground font-mono text-xs leading-relaxed">
                {errorMessage ?? "Unknown error"}
              </p>
              <p className="text-muted-foreground text-xs">
                Set <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">VITE_API_BASE_URL</code>{" "}
                to point to your FastAPI service (expects{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">GET /api/dashboard</code>)
                and ensure CORS allows this origin.
              </p>
            </div>
          )}

          {isEmpty && (
            <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-card/60 px-4 py-3 text-sm text-muted-foreground">
              <Inbox className="h-4 w-4" />
              <span>
                Connected, but no scheduling cycles have been recorded yet. Start your
                worker to populate the dashboard.
              </span>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
