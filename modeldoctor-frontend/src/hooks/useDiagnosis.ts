/* ────────────────────────────────────────
   useDiagnosis hook — state management
   for the diagnosis workflow
   ──────────────────────────────────────── */

"use client";

import { useState, useCallback } from "react";
import { diagnoseCode } from "@/lib/api";
import {
  DiagnosisResponse,
  DiagnosisState,
} from "@/lib/types";

export function useDiagnosis() {
  const [state, setState] = useState<DiagnosisState>("idle");
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runDiagnosis = useCallback(async (code: string) => {
    if (!code.trim() || code.trim().length < 10) {
      setError("Please enter at least 10 characters of Python ML code.");
      setState("error");
      return;
    }

    setState("scanning");
    setResult(null);
    setError(null);

    try {
      // 3-layer pipeline: Pattern Scanner + AST Deep Analyzer + Gemini
      const response = await diagnoseCode({ code, language: "python" });
      setResult(response);
      setState("success");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(message);
      setState("error");
    }
  }, []);


  const reset = useCallback(() => {
    setState("idle");
    setResult(null);
    setError(null);
  }, []);

  return { state, result, error, runDiagnosis, reset };
}
