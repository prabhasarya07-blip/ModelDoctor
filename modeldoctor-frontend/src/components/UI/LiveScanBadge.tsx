/* ────────────────────────────────────────
   LiveScanBadge — Compact inline indicator
   showing real-time Layer 1 scan status
   ──────────────────────────────────────── */

"use client";

import { QuickScanFlag } from "@/lib/types";

interface LiveScanBadgeProps {
  flags: QuickScanFlag[];
  scanning: boolean;
}

export default function LiveScanBadge({ flags, scanning }: LiveScanBadgeProps) {
  const criticalCount = flags.filter((f) => f.severity === "CRITICAL").length;
  const highCount = flags.filter((f) => f.severity === "HIGH").length;
  const warnCount = flags.filter((f) => f.severity === "MEDIUM" || f.severity === "LOW").length;
  const total = flags.length;

  if (scanning) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[10px] text-text-muted/50 font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
        Scanning...
      </span>
    );
  }

  if (total === 0) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[10px] text-accent-teal/60 font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-teal/60" />
        Clean
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2 text-[10px] font-mono">
      {criticalCount > 0 && (
        <span className="inline-flex items-center gap-1 text-accent-red">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-red" />
          {criticalCount}
        </span>
      )}
      {highCount > 0 && (
        <span className="inline-flex items-center gap-1 text-accent-orange">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-orange" />
          {highCount}
        </span>
      )}
      {warnCount > 0 && (
        <span className="inline-flex items-center gap-1 text-accent-yellow">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow" />
          {warnCount}
        </span>
      )}
      <span className="text-text-muted/40">live</span>
    </span>
  );
}
