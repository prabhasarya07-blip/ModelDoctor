/* ────────────────────────────────────────
   TypeScript interfaces for ModelDoctor
   ──────────────────────────────────────── */

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface IssueLocation {
  line_start: number | null;
  line_end: number | null;
  code_snippet: string | null;
}

export interface DiagnosisIssue {
  id: string;
  type: string;
  severity: Severity;
  title: string;
  explanation: string;
  suggested_fix: string;
  location: IssueLocation | null;
  health_impact: number;
  estimated_quality_impact: string;
  refactored_code?: string;
}

export interface PipelineStageSchema {
  name: string;
  line: number;
  details: Record<string, any>;
}

export interface DiagnosisResponse {
  health_score: number;
  issues: DiagnosisIssue[];
  pipeline_stages: PipelineStageSchema[];
  model_complexity_score: number;
  gpu_waste_risk: string;
  summary: string;
  diagnosis_time_ms: number;
  model_used: string;
}

export interface DiagnoseRequest {
  code: string;
  language: string;
  context?: {
    dataset_size?: string;
    model_type?: string;
    framework?: string;
  };
}

export type DiagnosisState = "idle" | "scanning" | "success" | "error";

/* ── Quick Scan (Layer 1 only) ── */

export interface QuickScanFlag {
  pattern_id: string;
  pattern_name: string;
  severity: Severity;
  description: string;
  line_number: number | null;
  matched_code: string | null;
  confidence: number;
}

export interface QuickScanResponse {
  flags: QuickScanFlag[];
  scan_time_ms: number;
}
