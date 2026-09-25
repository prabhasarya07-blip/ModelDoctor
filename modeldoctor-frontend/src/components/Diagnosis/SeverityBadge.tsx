/* ────────────────────────────────────────
   SeverityBadge — Color-coded pill badge
   ──────────────────────────────────────── */

"use client";

import { Severity } from "@/lib/types";

interface SeverityBadgeProps {
  severity: Severity;
}

const SEVERITY_CONFIG: Record<
  Severity,
  { bg: string; text: string; border: string }
> = {
  CRITICAL: {
    bg: "bg-accent-red/15",
    text: "text-accent-red",
    border: "border-accent-red/30",
  },
  HIGH: {
    bg: "bg-accent-orange/15",
    text: "text-accent-orange",
    border: "border-accent-orange/30",
  },
  MEDIUM: {
    bg: "bg-accent-yellow/15",
    text: "text-accent-yellow",
    border: "border-accent-yellow/30",
  },
  LOW: {
    bg: "bg-text-muted/15",
    text: "text-text-muted",
    border: "border-text-muted/30",
  },
};

export default function SeverityBadge({ severity }: SeverityBadgeProps) {
  const config = SEVERITY_CONFIG[severity];

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full
        text-[10px] font-bold uppercase tracking-wider
        border ${config.bg} ${config.text} ${config.border}
      `}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          severity === "CRITICAL"
            ? "bg-accent-red"
            : severity === "HIGH"
            ? "bg-accent-orange"
            : severity === "MEDIUM"
            ? "bg-accent-yellow"
            : "bg-text-muted"
        }`}
      />
      {severity}
    </span>
  );
}
