/* ────────────────────────────────────────
   SampleCodeLoader — Buttons to load
   pre-built buggy ML code examples
   ──────────────────────────────────────── */

"use client";

import { SAMPLE_CODES } from "@/lib/sample-codes";
import { motion } from "framer-motion";

interface SampleCodeLoaderProps {
  onLoad: (code: string) => void;
  disabled?: boolean;
}

export default function SampleCodeLoader({
  onLoad,
  disabled = false,
}: SampleCodeLoaderProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <span className="text-[10px] text-text-muted/50 self-center mr-0.5">
        Samples:
      </span>
      {SAMPLE_CODES.map((sample) => (
        <motion.button
          key={sample.id}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onLoad(sample.code)}
          disabled={disabled}
          className={`
            px-2.5 py-1 rounded-md text-[10px] font-medium
            border transition-all duration-200
            disabled:opacity-40 disabled:cursor-not-allowed
            ${
              sample.severity === "CRITICAL"
                ? "border-accent-red/20 text-accent-red/80 hover:bg-accent-red/10"
                : "border-accent-orange/20 text-accent-orange/80 hover:bg-accent-orange/10"
            }
          `}
          title={sample.description}
        >
          {sample.title}
        </motion.button>
      ))}
    </div>
  );
}
