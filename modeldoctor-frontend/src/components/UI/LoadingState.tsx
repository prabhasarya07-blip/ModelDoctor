/* ────────────────────────────────────────
   LoadingState — Premium scanning anim
   with orbital ring + step progress bar
   ──────────────────────────────────────── */

"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const STEPS = [
  { label: "Pattern Scan", icon: "🔍", duration: 1500 },
  { label: "Data Analysis", icon: "📊", duration: 2000 },
  { label: "AI Reasoning", icon: "🧠", duration: 4000 },
  { label: "Building Report", icon: "📋", duration: 2000 },
];

export default function LoadingState() {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (currentStep < STEPS.length - 1) {
      timeout = setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, STEPS[currentStep].duration);
    }
    return () => clearTimeout(timeout);
  }, [currentStep]);

  const progress = ((currentStep + 1) / STEPS.length) * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      className="glass-strong rounded-2xl p-8 text-center"
    >
      {/* Orbital ring animation */}
      <div className="relative w-28 h-28 mx-auto mb-6">
        {/* Glow halo */}
        <div className="absolute inset-0 rounded-full bg-accent-blue/10 blur-xl" />

        {/* Static track */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="44" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="2" />
        </svg>

        {/* Spinning arc */}
        <motion.svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 100 100"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <defs>
            <linearGradient id="arc-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0" />
              <stop offset="50%" stopColor="#3B82F6" />
              <stop offset="100%" stopColor="#00C9A7" />
            </linearGradient>
          </defs>
          <circle
            cx="50" cy="50" r="44" fill="none"
            stroke="url(#arc-grad)" strokeWidth="2.5"
            strokeLinecap="round"
            strokeDasharray="70 207"
          />
        </motion.svg>

        {/* Inner pulse */}
        <motion.div
          className="absolute inset-6 rounded-full bg-accent-blue/5"
          animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2.5, repeat: Infinity }}
        />

        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center text-2xl">
          <AnimatePresence mode="wait">
            <motion.span
              key={currentStep}
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.5, opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              {STEPS[currentStep].icon}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>

      {/* Title */}
      <h3 className="text-base font-bold text-text-primary mb-1">
        Scanning Pipeline
        <motion.span
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          ...
        </motion.span>
      </h3>
      <p className="text-xs text-text-muted/60 mb-5">
        Analyzing for silent ML failures
      </p>

      {/* Progress bar */}
      <div className="max-w-xs mx-auto mb-4">
        <div className="h-1 rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-accent-blue to-accent-teal"
            initial={{ width: "0%" }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-center gap-1.5">
        {STEPS.map((step, i) => (
          <div key={step.label} className="flex items-center gap-1.5">
            <div
              className={`
                flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium
                transition-all duration-400
                ${
                  i < currentStep
                    ? "bg-accent-teal/10 text-accent-teal"
                    : i === currentStep
                    ? "bg-accent-blue/15 text-accent-blue"
                    : "bg-white/[0.03] text-text-muted/40"
                }
              `}
            >
              {i < currentStep ? (
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20,6 9,17 4,12" />
                </svg>
              ) : i === currentStep ? (
                <motion.div
                  className="w-1.5 h-1.5 rounded-full bg-accent-blue"
                  animate={{ scale: [1, 1.4, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full bg-text-muted/30" />
              )}
              {step.label}
            </div>
            {i < STEPS.length - 1 && (
              <div className={`w-3 h-px ${i < currentStep ? "bg-accent-teal/30" : "bg-white/[0.06]"}`} />
            )}
          </div>
        ))}
      </div>
    </motion.div>
  );
}
