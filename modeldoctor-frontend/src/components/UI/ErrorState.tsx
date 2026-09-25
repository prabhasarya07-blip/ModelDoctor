/* ────────────────────────────────────────
   ErrorState — Error display component
   ──────────────────────────────────────── */

"use client";

import { motion } from "framer-motion";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass rounded-2xl p-8 text-center border border-accent-red/20"
    >
      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-red/10 flex items-center justify-center">
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#FF2244"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      </div>
      <h3 className="text-lg font-bold text-accent-red mb-2">
        Diagnosis Failed
      </h3>
      <p className="text-sm text-text-muted mb-4 max-w-md mx-auto">
        {message}
      </p>
      <button
        onClick={onRetry}
        className="px-4 py-2 rounded-lg text-xs font-medium bg-accent-red/10 text-accent-red
          border border-accent-red/20 hover:bg-accent-red/20 transition-colors"
      >
        Try Again
      </button>
    </motion.div>
  );
}
