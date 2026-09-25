/* ────────────────────────────────────────
   DiagnosisReport — Premium results panel
   with glass-strong, gradient accents,
   and Export Report button
   ──────────────────────────────────────── */

"use client";

import { useCallback } from "react";
import { motion } from "framer-motion";
import { DiagnosisResponse } from "@/lib/types";
import { downloadReport } from "@/lib/report-export";
import HealthScore from "./HealthScore";
import IssueCard from "./IssueCard";

interface DiagnosisReportProps {
  report: DiagnosisResponse;
}

export default function DiagnosisReport({ report }: DiagnosisReportProps) {
  const criticalCount = report.issues.filter((i) => i.severity === "CRITICAL").length;
  const highCount = report.issues.filter((i) => i.severity === "HIGH").length;
  const mediumCount = report.issues.filter((i) => i.severity === "MEDIUM").length;
  const lowCount = report.issues.filter((i) => i.severity === "LOW").length;

  const handleExport = useCallback(() => {
    downloadReport(report);
  }, [report]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="space-y-5"
    >
      {/* ── Score card ── */}
      <div className="glass-strong rounded-2xl p-6 gradient-border">
        <div className="flex flex-col lg:flex-row items-center gap-6">
          <HealthScore score={report.health_score} />

          <div className="flex-1 text-center lg:text-left space-y-3">
            {/* Severity pills */}
            <div className="flex flex-wrap gap-2 justify-center lg:justify-start">
              {criticalCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-red/10 text-accent-red text-[11px] font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-red" />
                  {criticalCount} Critical
                </span>
              )}
              {highCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-orange/10 text-accent-orange text-[11px] font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-orange" />
                  {highCount} High
                </span>
              )}
              {mediumCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-yellow/10 text-accent-yellow text-[11px] font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-accent-yellow" />
                  {mediumCount} Medium
                </span>
              )}
              {lowCount > 0 && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.05] text-text-muted text-[11px] font-semibold">
                  <span className="w-1.5 h-1.5 rounded-full bg-text-muted" />
                  {lowCount} Low
                </span>
              )}
            </div>

            {/* Summary */}
            <p className="text-sm text-text-primary/75 leading-relaxed">
              {report.summary}
            </p>

            {/* Meta */}
            <div className="flex flex-wrap gap-3 items-center text-[10px] text-text-muted/60 font-mono">
              <span>⚡ {(report.diagnosis_time_ms / 1000).toFixed(1)}s</span>
              <span>🧠 {report.model_used}</span>
              <span>📊 {report.issues.length} issues</span>
              <span>⚙️ Complexity: {report.model_complexity_score}/10</span>
              <span>💽 GPU Waste: {report.gpu_waste_risk}</span>
              <button
                onClick={handleExport}
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-accent-blue/15 to-accent-teal/15 hover:from-accent-blue/25 hover:to-accent-teal/25 text-accent-blue text-[11px] font-semibold transition-all border border-accent-blue/10"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="7,10 12,15 17,10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Export Report
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Pipeline Workflow ── */}
      {report.pipeline_stages && report.pipeline_stages.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-blue/80">
              <path d="M6 3v12a3 3 0 0 0 3 3h12" />
              <polyline points="16 13 21 18 16 23" />
            </svg>
            Pipeline Workflow
          </h3>
          <div className="flex flex-wrap gap-2 items-center">
            {report.pipeline_stages.map((stage, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="glass-strong px-3 py-1.5 rounded-lg text-[11px] font-mono text-text-primary/80 border border-white/5 flex flex-col">
                  <span className="uppercase text-accent-blue/80 font-bold tracking-wider">{stage.name}</span>
                  <span className="text-text-muted/50 mt-0.5">Line {stage.line}</span>
                </div>
                {i < report.pipeline_stages.length - 1 && (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-text-muted/30">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Issue list ── */}
      {report.issues.length > 0 && (
        <div>
          <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-2">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-red/60">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            Detected Issues
          </h3>

          <div className="space-y-2">
            {report.issues.map((issue, index) => (
              <IssueCard key={issue.id} issue={issue} index={index} />
            ))}
          </div>
        </div>
      )}

      {/* ── Clean bill of health ── */}
      {report.issues.length === 0 && report.health_score >= 80 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-strong rounded-2xl p-8 text-center glow-teal"
        >
          <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-accent-teal/15 flex items-center justify-center">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#00C9A7" strokeWidth="2.5">
              <polyline points="20,6 9,17 4,12" />
            </svg>
          </div>
          <h3 className="text-lg font-bold gradient-text mb-2">
            Pipeline Looks Healthy!
          </h3>
          <p className="text-sm text-text-muted max-w-xs mx-auto">
            No significant silent failures detected. Your ML pipeline follows
            good practices.
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
