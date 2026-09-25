/* ────────────────────────────────────────
   DiagnoseButton — Premium CTA with gradient
   ──────────────────────────────────────── */

"use client";

import { motion } from "framer-motion";

interface DiagnoseButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export default function DiagnoseButton({
  onClick,
  disabled = false,
  loading = false,
}: DiagnoseButtonProps) {
  return (
    <motion.button
      whileHover={disabled ? {} : { scale: 1.02 }}
      whileTap={disabled ? {} : { scale: 0.97 }}
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        relative group px-7 py-3 rounded-xl font-semibold text-sm tracking-wide
        transition-all duration-300 overflow-hidden
        disabled:opacity-40 disabled:cursor-not-allowed
        ${loading
          ? "bg-accent-blue/20 text-accent-blue border border-accent-blue/20"
          : "bg-gradient-to-r from-accent-blue to-accent-blue/80 text-white shadow-lg shadow-accent-blue/25 hover:shadow-accent-blue/40"
        }
      `}
    >
      {/* Shimmer overlay on hover */}
      {!loading && (
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
          <div className="absolute inset-0 shimmer" />
        </div>
      )}

      <span className="relative flex items-center gap-2.5">
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeLinecap="round" />
            </svg>
            Scanning...
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Run Diagnosis
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded bg-white/15 text-[10px] font-normal ml-1">
              Ctrl+Enter
            </kbd>
          </>
        )}
      </span>
    </motion.button>
  );
}
