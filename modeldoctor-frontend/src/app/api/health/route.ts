/* ────────────────────────────────────────
   GET /api/health — health check + service info.
   Port of the FastAPI `/` and `/health` routes.
   ──────────────────────────────────────── */

import { NextResponse } from "next/server";
import { MODEL_USED } from "@/lib/server/engine";
import { PATTERNS } from "@/lib/server/pattern-scanner";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    name: "ModelDoctor API",
    version: "2.0.0",
    tagline: "The MRI for your ML pipeline.",
    team: "ASTROID — Prabhas N & Poornima Bhat",
    architecture: "3-Layer Pipeline: Pattern Scanner → Data Analyzer → Rules Engine",
    status: "healthy",
    engine: MODEL_USED,
    pattern_count: PATTERNS.length,
  });
}
