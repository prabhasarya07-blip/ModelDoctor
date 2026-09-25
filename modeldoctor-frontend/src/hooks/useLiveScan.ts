/* ────────────────────────────────────────
   useLiveScan — Debounced real-time
   Layer 1 pattern scanner (no Gemini)
   ──────────────────────────────────────── */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { quickScanWithSignal } from "@/lib/api";
import { QuickScanFlag } from "@/lib/types";

const DEBOUNCE_MS = 600; // Wait 600ms after user stops typing

export function useLiveScan(code: string, enabled: boolean = true) {
  const [flags, setFlags] = useState<QuickScanFlag[]>([]);
  const [scanning, setScanning] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const clear = useCallback(() => {
    setFlags([]);
  }, []);

  useEffect(() => {
    if (!enabled || code.trim().length < 20) {
      setFlags([]);
      return;
    }

    // Cancel previous timer
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(async () => {
      // Cancel previous in-flight request
      if (abortRef.current) abortRef.current.abort();
      abortRef.current = new AbortController();

      setScanning(true);
      try {
        const result = await quickScanWithSignal(code, abortRef.current?.signal);
        setFlags(result.flags);
      } catch {
        // Silently ignore — this is a background scan
      } finally {
        setScanning(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [code, enabled]);

  return { flags, scanning, clear };
}
