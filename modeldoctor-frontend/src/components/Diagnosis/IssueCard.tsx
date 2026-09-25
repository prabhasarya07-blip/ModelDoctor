/* ────────────────────────────────────────
   IssueCard — Premium finding card
   with gradient stripe, expand & Copy Fix
   ──────────────────────────────────────── */

"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { DiagnosisIssue } from "@/lib/types";
import SeverityBadge from "./SeverityBadge";

interface IssueCardProps {
  issue: DiagnosisIssue;
  index: number;
}

export default function IssueCard({ issue, index }: IssueCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyFix = useCallback(async () => {
    if (!issue.suggested_fix) return;
    try {
      await navigator.clipboard.writeText(issue.suggested_fix);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = issue.suggested_fix;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [issue.suggested_fix]);

  const stripeClass =
    issue.severity === "CRITICAL" ? "issue-stripe-critical" :
      issue.severity === "HIGH" ? "issue-stripe-high" :
        issue.severity === "MEDIUM" ? "issue-stripe-medium" : "issue-stripe-low";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.1 }}
      className={`glass-strong rounded-xl ${stripeClass} transition-all duration-300 overflow-hidden hover:bg-white/[0.02]`}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        <span className="flex-shrink-0 w-6 h-6 rounded-md bg-white/[0.05] flex items-center justify-center text-[10px] font-bold text-text-muted font-mono">
          {index + 1}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <SeverityBadge severity={issue.severity} />
            <span className="text-[10px] text-text-muted/60 font-mono uppercase tracking-wider">
              {issue.type.replace(/_/g, " ")}
            </span>
            {issue.location?.line_start && (
              <span className="text-[10px] text-text-muted/40 font-mono">
                L{issue.location.line_start}
                {issue.location.line_end && issue.location.line_end !== issue.location.line_start
                  ? `–${issue.location.line_end}` : ""}
              </span>
            )}
          </div>
          <h4 className="text-sm font-semibold text-text-primary leading-snug">
            {issue.title}
          </h4>
        </div>

        <motion.svg
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2"
          className="flex-shrink-0 text-text-muted/40 mt-1.5"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <polyline points="6,9 12,15 18,9" />
        </motion.svg>
      </button>

      {/* Expanded */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3 border-t border-white/[0.04] pt-3 ml-9">
              {/* Explanation */}
              <div>
                <h5 className="text-[10px] uppercase tracking-wider text-text-muted/60 mb-1 font-semibold">
                  Why This Matters
                </h5>
                <p className="text-xs text-text-primary/70 leading-relaxed">
                  {issue.explanation}
                </p>
              </div>

              {/* Problem code */}
              {issue.location?.code_snippet && (
                <div>
                  <h5 className="text-[10px] uppercase tracking-wider text-accent-red/70 mb-1 font-semibold">
                    Problem Code
                  </h5>
                  <pre className="bg-void/60 rounded-lg p-3 text-xs overflow-x-auto border border-accent-red/10 font-mono">
                    <code className="text-accent-red/70">{issue.location.code_snippet}</code>
                  </pre>
                </div>
              )}

              {/* Fix */}
              {issue.suggested_fix && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h5 className="text-[10px] uppercase tracking-wider text-accent-teal/70 font-semibold">
                      Suggested Fix
                    </h5>
                    <button
                      onClick={handleCopyFix}
                      className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-accent-teal/10 hover:bg-accent-teal/20 text-accent-teal text-[10px] font-semibold transition-colors"
                    >
                      {copied ? (
                        <>
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polyline points="20,6 9,17 4,12" />
                          </svg>
                          Copied!
                        </>
                      ) : (
                        <>
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                          </svg>
                          Copy Fix
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="bg-void/60 rounded-lg p-3 text-xs overflow-x-auto border border-accent-teal/10 font-mono flex flex-col">
                    <code className="text-accent-teal/70">{issue.suggested_fix}</code>
                  </pre>
                </div>
              )}

              {/* Refactored Code */}
              {issue.refactored_code && (
                <div className="mt-3">
                  <h5 className="text-[10px] uppercase tracking-wider text-accent-blue/70 mb-1 font-semibold flex items-center gap-1.5">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                    Auto-Refactored Code
                  </h5>
                  <pre className="bg-void/60 rounded-lg p-3 text-xs overflow-x-auto border border-accent-blue/10 font-mono">
                    <code className="text-accent-blue/70 whitespace-pre">{issue.refactored_code}</code>
                  </pre>
                </div>
              )}

              {/* Impact */}
              <div className="flex flex-col gap-2 pt-2 border-t border-white/[0.02] mt-2">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-wider text-text-muted/50 font-semibold w-24">
                    Health Score
                  </span>
                  <span className="text-xs font-bold text-accent-red font-mono">
                    {issue.health_impact > 0 ? "-" : ""}{Math.abs(issue.health_impact)} pts
                  </span>
                </div>
                {issue.estimated_quality_impact && issue.estimated_quality_impact !== "Unknown" && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-text-muted/50 font-semibold w-24">
                      Real-World
                    </span>
                    <span className="text-[11px] font-medium text-accent-orange">
                      {issue.estimated_quality_impact}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
