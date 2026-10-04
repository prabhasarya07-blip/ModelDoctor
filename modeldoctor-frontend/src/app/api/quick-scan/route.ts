/* ────────────────────────────────────────
   POST /api/quick-scan — Layer 1 only.
   Used for real-time editor feedback.
   ──────────────────────────────────────── */

import { NextResponse } from "next/server";
import { QuickScanFlag } from "@/lib/types";
import { scanCode } from "@/lib/server/pattern-scanner";
import { MAX_CODE_LENGTH } from "@/lib/server/engine";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 10;

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ flags: [], scan_time_ms: 0 });
  }

  const code = (body as { code?: unknown } | null)?.code;
  if (typeof code !== "string") {
    return NextResponse.json({ flags: [], scan_time_ms: 0 });
  }

  const trimmed = code.trim();
  if (trimmed.length < 10 || trimmed.length > MAX_CODE_LENGTH) {
    return NextResponse.json({ flags: [], scan_time_ms: 0 });
  }

  const t0 = performance.now();
  let flags: QuickScanFlag[] = [];
  try {
    flags = scanCode(trimmed);
  } catch (err) {
    console.error("Quick scan failed:", err);
  }
  const scanTimeMs = Math.round((performance.now() - t0) * 100) / 100;

  return NextResponse.json({ flags, scan_time_ms: scanTimeMs });
}
