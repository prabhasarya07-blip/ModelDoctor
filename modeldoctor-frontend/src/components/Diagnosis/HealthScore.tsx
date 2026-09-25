/* ────────────────────────────────────────
   HealthScore — Glowing SVG ring gauge
   with count-up and grade display
   ──────────────────────────────────────── */

"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";

interface HealthScoreProps {
  score: number;
}

export default function HealthScore({ score }: HealthScoreProps) {
  const [displayScore, setDisplayScore] = useState(0);
  const animationRef = useRef<number | null>(null);

  const size = 180;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const getColor = (s: number) => {
    if (s < 40) return { main: "#FF2244", glow: "rgba(255, 34, 68, 0.3)" };
    if (s < 65) return { main: "#FF5500", glow: "rgba(255, 85, 0, 0.3)" };
    return { main: "#00DEB4", glow: "rgba(0, 222, 180, 0.3)" };
  };

  const getGrade = (s: number) => {
    if (s >= 90) return "A";
    if (s >= 80) return "B";
    if (s >= 65) return "C";
    if (s >= 50) return "D";
    return "F";
  };

  const getLabel = (s: number) => {
    if (s < 30) return "Critical";
    if (s < 50) return "Poor";
    if (s < 65) return "Needs Work";
    if (s < 80) return "Fair";
    if (s < 90) return "Good";
    return "Excellent";
  };

  const { main: color, glow } = getColor(score);

  useEffect(() => {
    const duration = 1200;
    const start = performance.now();
    const animate = (time: number) => {
      const elapsed = time - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(eased * score));
      if (progress < 1) animationRef.current = requestAnimationFrame(animate);
    };
    animationRef.current = requestAnimationFrame(animate);
    return () => { if (animationRef.current) cancelAnimationFrame(animationRef.current); };
  }, [score]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay: 0.15 }}
      className="flex flex-col items-center"
    >
      <div className="relative" style={{ width: size, height: size }}>
        {/* Glow behind ring */}
        <div
          className="absolute inset-4 rounded-full blur-xl"
          style={{ background: glow, opacity: 0.4 }}
        />

        <svg width={size} height={size} className="transform -rotate-90 relative z-10">
          {/* Background ring */}
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={strokeWidth}
          />
          {/* Score ring */}
          <motion.circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: "easeOut", delay: 0.2 }}
            style={{ filter: `drop-shadow(0 0 6px ${glow})` }}
          />
        </svg>

        {/* Center */}
        <div className="absolute inset-0 flex flex-col items-center justify-center z-10">
          <span className="text-4xl font-bold tabular-nums font-mono" style={{ color }}>
            {displayScore}
          </span>
          <span className="text-[10px] text-text-muted mt-0.5 font-medium">/ 100</span>
        </div>
      </div>

      {/* Grade + Label */}
      <div className="mt-3 text-center">
        <div className="flex items-center justify-center gap-2">
          <span
            className="text-lg font-bold font-mono"
            style={{ color }}
          >
            {getGrade(score)}
          </span>
          <span className="text-xs text-text-muted">•</span>
          <span className="text-xs font-medium" style={{ color }}>
            {getLabel(score)}
          </span>
        </div>
        <p className="text-[10px] text-text-muted/60 mt-0.5 uppercase tracking-wider font-medium">
          Pipeline Health
        </p>
      </div>
    </motion.div>
  );
}
