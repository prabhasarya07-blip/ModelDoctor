/* ────────────────────────────────────────
   POST /api/diagnose — the core ModelDoctor endpoint.
   Port of the FastAPI route in routers/diagnose.py.
   ──────────────────────────────────────── */

import { NextResponse } from "next/server";
import { MAX_CODE_LENGTH, runDiagnosis, validateCode } from "@/lib/server/engine";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

export async function POST(request: Request) {
  const startedAt = performance.now();

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 }
    );
  }

  const code = (body as { code?: unknown } | null)?.code;

  if (typeof code !== "string") {
    return NextResponse.json(
      { detail: "Field 'code' is required and must be a string." },
      { status: 400 }
    );
  }
  if (code.length > MAX_CODE_LENGTH) {
    return NextResponse.json(
      { detail: `Code too long (${code.length.toLocaleString()} chars). Maximum is ${MAX_CODE_LENGTH.toLocaleString()} characters.` },
      { status: 400 }
    );
  }

  try {
    const result = runDiagnosis(validateCode(code));
    const elapsedMs = Math.round(performance.now() - startedAt);
    return NextResponse.json(result, {
      headers: { "X-Process-Time-Ms": String(elapsedMs) },
    });
  } catch (err) {
    const detail = err instanceof Error ? err.message : "Internal server error.";
    const isValidation = detail.startsWith("Code too");
    return NextResponse.json(
      { detail, error_type: isValidation ? "ValidationError" : "InternalError" },
      { status: isValidation ? 400 : 500 }
    );
  }
}
