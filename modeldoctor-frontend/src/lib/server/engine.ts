/* ────────────────────────────────────────
   5-Layer Diagnosis Pipeline (Rules Engine V2).
   Port of routers/diagnose.py::_run_diagnosis_v2
   ──────────────────────────────────────── */

import { DiagnosisResponse, DiagnosisIssue } from "@/lib/types";
import { parseCode } from "./parser";
import { analyzePipeline } from "./pipeline-analyzer";
import {
  calculateScore,
  dataLeakageRule,
  bestPracticesRule,
  overfittingRule,
  runAllRules,
} from "./rules";

export const MAX_CODE_LENGTH = 50_000;
export const MIN_CODE_LENGTH = 10;
export const MODEL_USED = "ModelDoctor Rules Engine V2";

const LAYER_CONSTRUCTORS = new Set([
  "Dense", "Conv2d", "LSTM", "Linear", "TransformerEncoder",
]);

/** Validate and sanitize code input. Returns cleaned code or throws. */
export function validateCode(input: unknown): string {
  const code = typeof input === "string" ? input.trim() : "";
  if (code.length < MIN_CODE_LENGTH) {
    throw new Error(
      `Code too short for meaningful analysis. Please provide at least ${MIN_CODE_LENGTH} characters.`
    );
  }
  if (code.length > MAX_CODE_LENGTH) {
    throw new Error(
      `Code too long (${code.length.toLocaleString()} chars). Maximum is ${MAX_CODE_LENGTH.toLocaleString()} characters.`
    );
  }
  return code;
}

export function runDiagnosis(code: string): DiagnosisResponse {
  const pipelineStart = performance.now();

  try {
    // Layer 1 & 2: abstract understanding
    const parsed = parseCode(code);
    const evidence = analyzePipeline(parsed);

    // Layer 3: rule checks
    const issues = runAllRules(
      [dataLeakageRule, overfittingRule, bestPracticesRule],
      parsed,
      evidence
    );

    // Layer 4: scoring
    const healthScore = calculateScore(issues);

    // Layer 5: report generation
    const totalMs = Math.round(performance.now() - pipelineStart);

    const summary =
      `Analyzed ${parsed.callsInOrder.length} ML operations logic map. ` +
      `Found ${issues.length} pipeline flaws. ` +
      `Detected ML Stage: ${evidence.codeType === "production" ? "Production" : "Research/Experimentation"}.`;

    const pipelineStages = evidence.stages.map((s) => ({
      name: s.name,
      line: s.line,
      details: s.details,
    }));

    // Model complexity: deeper stacks are more complex.
    const layerCount = parsed.callsInOrder.filter((c) =>
      LAYER_CONSTRUCTORS.has(c.function ?? "")
    ).length;
    const modelComplexityScore = Math.min(10, Math.max(1, Math.floor(layerCount / 2) + 1));

    // Compute waste risk
    let gpuWaste = "Low";
    if (layerCount > 3) {
      const hasDevice = parsed.callsInOrder.some(
        (c) => c.method === "to" || c.method === "cuda"
      );
      gpuWaste = hasDevice ? "Low" : "High (Deep network, no GPU device mapped)";
    }

    return {
      health_score: healthScore,
      issues: issues as DiagnosisIssue[],
      pipeline_stages: pipelineStages,
      model_complexity_score: modelComplexityScore,
      gpu_waste_risk: gpuWaste,
      summary,
      diagnosis_time_ms: totalMs,
      model_used: MODEL_USED,
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("Diagnosis failed:", err);
    return {
      health_score: 0,
      issues: [],
      pipeline_stages: [],
      model_complexity_score: 1,
      gpu_waste_risk: "Low",
      summary: `Analysis encountered an error. Please try again. (${message})`,
      diagnosis_time_ms: Math.round(performance.now() - pipelineStart),
      model_used: MODEL_USED,
    };
  }
}
