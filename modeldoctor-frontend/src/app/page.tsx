"use client";

import { useState, useCallback, useEffect, type ReactNode, type MouseEvent } from "react";
import {
  AnimatePresence,
  motion,
  type HTMLMotionProps,
  useMotionValue,
  useMotionTemplate,
  useSpring,
  useReducedMotion,
  useScroll,
} from "framer-motion";
import dynamic from "next/dynamic";
import Header from "@/components/Layout/Header";
import MLSignalsShowcase from "@/components/Layout/MLSignalsShowcase";
const NeuralBackground = dynamic(() => import("@/components/Layout/NeuralBackground"), { ssr: false });
import CodeEditor from "@/components/Editor/CodeEditor";
import SampleCodeLoader from "@/components/Editor/SampleCodeLoader";
import DiagnoseButton from "@/components/UI/DiagnoseButton";
import LiveScanBadge from "@/components/UI/LiveScanBadge";
import LoadingState from "@/components/UI/LoadingState";
import ErrorState from "@/components/UI/ErrorState";
import DiagnosisReport from "@/components/Diagnosis/DiagnosisReport";
import { useDiagnosis } from "@/hooks/useDiagnosis";
import { useLiveScan } from "@/hooks/useLiveScan";
import { SAMPLE_CODES } from "@/lib/sample-codes";

const DEFAULT_CODE = SAMPLE_CODES[0].code;

const HERO_STATS = [
  { label: "Silent failure patterns", value: "120+" },
  { label: "Average scan speed", value: "2.8s" },
  { label: "Teams using workflow", value: "24" },
];

const BENEFIT_ITEMS = [
  {
    title: "Traceable diagnosis flow",
    description: "See exactly where your pipeline breaks trust before model metrics degrade in production.",
  },
  {
    title: "Live pre-check intelligence",
    description: "Catch risky code lines while typing, then run full diagnosis with one click or Ctrl+Enter.",
  },
  {
    title: "Exportable evidence",
    description: "Generate report snapshots to share findings with teammates and MLOps reviewers quickly.",
  },
];

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12, delayChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const },
  },
};

interface TiltPanelProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
}

function TiltPanel({ className, children, style, ...rest }: TiltPanelProps) {
  const shouldReduceMotion = useReducedMotion();
  const rotateX = useMotionValue(0);
  const rotateY = useMotionValue(0);
  const springX = useSpring(rotateX, { stiffness: 240, damping: 20, mass: 0.4 });
  const springY = useSpring(rotateY, { stiffness: 240, damping: 20, mass: 0.4 });

  const handleMove = (event: MouseEvent<HTMLDivElement>) => {
    if (shouldReduceMotion || window.innerWidth < 1024) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const offsetX = event.clientX - bounds.left;
    const offsetY = event.clientY - bounds.top;
    const y = ((offsetX / bounds.width) * 2 - 1) * 4;
    const x = ((offsetY / bounds.height) * 2 - 1) * -4;
    rotateX.set(x);
    rotateY.set(y);
  };

  const handleLeave = () => {
    rotateX.set(0);
    rotateY.set(0);
  };

  return (
    <motion.div
      {...rest}
      className={className}
      style={{ ...style, rotateX: springX, rotateY: springY, transformStyle: "preserve-3d" }}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      whileHover={shouldReduceMotion ? undefined : { y: -3 }}
    >
      {children}
    </motion.div>
  );
}

export default function HomePage() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const shouldReduceMotion = useReducedMotion();
  const { state, result, error, runDiagnosis, reset } = useDiagnosis();
  const { flags: liveFlags, scanning: liveScanActive } = useLiveScan(code, state !== "scanning");
  const { scrollYProgress } = useScroll();
  const progressScaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 26, mass: 0.25 });
  const mouseX = useMotionValue(-1000);
  const mouseY = useMotionValue(-1000);
  const spotlightX = useSpring(mouseX, { stiffness: 220, damping: 40, mass: 0.2 });
  const spotlightY = useSpring(mouseY, { stiffness: 220, damping: 40, mass: 0.2 });
  const spotlight = useMotionTemplate`radial-gradient(520px circle at ${spotlightX}px ${spotlightY}px, rgba(66, 133, 244, 0.16), transparent 65%)`;

  const handleDiagnose = useCallback(() => {
    runDiagnosis(code);
  }, [code, runDiagnosis]);

  const handleLoadSample = useCallback(
    (sampleCode: string) => {
      setCode(sampleCode);
      reset();
    },
    [reset]
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (state !== "scanning") {
          handleDiagnose();
        }
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleDiagnose, state]);

  const handleMouseMove = (event: MouseEvent<HTMLDivElement>) => {
    if (shouldReduceMotion) return;
    mouseX.set(event.clientX);
    mouseY.set(event.clientY);
  };

  const handleMouseLeave = () => {
    mouseX.set(-1000);
    mouseY.set(-1000);
  };

  return (
    <div
      className="min-h-screen bg-void relative overflow-hidden"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <motion.div className="scroll-progress" style={{ scaleX: progressScaleX }} />
      <NeuralBackground />
      <div className="aurora-overlay" />
      <div className="noise-overlay" />
      <div className="floating-orb floating-orb-blue" />
      <div className="floating-orb floating-orb-red" />
      {!shouldReduceMotion && <motion.div className="pointer-spotlight" style={{ background: spotlight }} />}

      <div className="relative z-10 flex flex-col min-h-screen">
        <Header />

        <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-8 sm:space-y-10">
          <motion.section
            initial="hidden"
            animate="show"
            variants={containerVariants}
            className="text-center space-y-6"
          >
            <motion.div variants={itemVariants} className="flex items-center justify-center">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-accent-blue/20 bg-accent-blue/10 text-[11px] uppercase tracking-[0.16em] text-accent-blue/80">
                <span className="w-1.5 h-1.5 rounded-full bg-accent-teal animate-pulse-dot" />
                Dynamic AI pipeline diagnosis
              </div>
            </motion.div>

            <motion.div variants={itemVariants} className="space-y-3">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-tight">
                <span className="gradient-text-red">Ship Better Models</span>
                <br />
                <span className="text-text-primary">Before They Reach Production</span>
              </h2>
              <p className="text-sm sm:text-base text-text-muted/75 max-w-2xl mx-auto leading-relaxed">
                ModelDoctor continuously inspects your training pipeline for leakages, overfitting traps, and
                hidden quality debt with fast, actionable diagnosis.
              </p>
            </motion.div>

            <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-3xl mx-auto">
              {HERO_STATS.map((item) => (
                <motion.div
                  key={item.label}
                  whileHover={shouldReduceMotion ? undefined : { y: -6, scale: 1.02 }}
                  className="glass rounded-xl p-4 border border-white/10 transition-all stat-card"
                >
                  <p className="text-lg font-bold text-text-primary">{item.value}</p>
                  <p className="text-[11px] uppercase tracking-[0.12em] text-text-muted/70 mt-1">{item.label}</p>
                </motion.div>
              ))}
            </motion.div>
          </motion.section>

          <div className="marquee-track py-2 overflow-hidden">
            <div className="marquee-inner text-[11px] uppercase tracking-[0.2em] text-text-muted/60 font-medium">
              <span>Leakage Detection</span>
              <span>Feature Drift Signals</span>
              <span>Pipeline Complexity Watch</span>
              <span>GPU Waste Alerts</span>
              <span>Explainable Issue Traces</span>
              <span>Leakage Detection</span>
              <span>Feature Drift Signals</span>
              <span>Pipeline Complexity Watch</span>
            </div>
          </div>

          <MLSignalsShowcase />

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TiltPanel
              initial={{ opacity: 0, x: -22 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
              className="space-y-4 glass-strong rounded-3xl p-4 sm:p-5 border border-white/10"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">Your ML Code</h3>
                <SampleCodeLoader onLoad={handleLoadSample} disabled={state === "scanning"} />
              </div>

              <CodeEditor code={code} onChange={setCode} disabled={state === "scanning"} liveFlags={liveFlags} />

              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <p className="text-[10px] text-text-muted/50 font-mono">
                    {code.split("\n").length} lines &middot; Python
                  </p>
                  <LiveScanBadge flags={liveFlags} scanning={liveScanActive} />
                </div>
                <DiagnoseButton onClick={handleDiagnose} loading={state === "scanning"} disabled={!code.trim()} />
              </div>
            </TiltPanel>

            <TiltPanel
              initial={{ opacity: 0, x: 22 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, amount: 0.15 }}
              transition={{ duration: 0.55, delay: 0.06, ease: [0.22, 1, 0.36, 1] }}
              className="glass-strong rounded-3xl p-4 sm:p-5 border border-white/10"
            >
              <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-4">Diagnosis Report</h3>

              <AnimatePresence mode="wait">
                {state === "idle" && (
                  <motion.div
                    key="idle"
                    initial={{ opacity: 0, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="glass rounded-2xl p-10 text-center"
                  >
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-accent-blue/10 to-accent-teal/10 flex items-center justify-center">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="url(#idleGrad)" strokeWidth="1.5">
                        <defs>
                          <linearGradient id="idleGrad" x1="0" y1="0" x2="24" y2="24">
                            <stop offset="0%" stopColor="#3B82F6" />
                            <stop offset="100%" stopColor="#00C9A7" />
                          </linearGradient>
                        </defs>
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                      </svg>
                    </div>
                    <h3 className="text-base font-bold text-text-primary/80 mb-1.5">Ready to Diagnose</h3>
                    <p className="text-xs text-text-muted/50 max-w-xs mx-auto leading-relaxed">
                      Click <span className="text-accent-blue font-semibold">Run Diagnosis</span> or press{" "}
                      <kbd className="px-1.5 py-0.5 rounded bg-white/[0.06] text-text-muted/60 text-[10px] font-mono">
                        Ctrl+Enter
                      </kbd>{" "}
                      to scan your code.
                    </p>
                  </motion.div>
                )}

                {state === "scanning" && (
                  <motion.div key="scanning" exit={{ opacity: 0, y: 8 }}>
                    <LoadingState />
                  </motion.div>
                )}

                {state === "error" && error && (
                  <motion.div key="error" exit={{ opacity: 0, y: 8 }}>
                    <ErrorState message={error} onRetry={handleDiagnose} />
                  </motion.div>
                )}

                {state === "success" && result && (
                  <motion.div key="success" exit={{ opacity: 0, y: 8 }} className="space-y-4">
                    <DiagnosisReport report={result} />
                  </motion.div>
                )}
              </AnimatePresence>
            </TiltPanel>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {BENEFIT_ITEMS.map((item, index) => (
              <motion.article
                key={item.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.25 }}
                transition={{ duration: 0.45, delay: index * 0.08 }}
                whileHover={{ y: -4, scale: 1.01 }}
                className="glass rounded-2xl p-5 border border-white/10 relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-accent-blue/[0.06] via-transparent to-accent-red/[0.04] pointer-events-none" />
                <p className="relative text-[11px] uppercase tracking-[0.16em] text-accent-blue/70 mb-2">
                  Advantage {index + 1}
                </p>
                <h3 className="relative text-base font-semibold text-text-primary mb-2">{item.title}</h3>
                <p className="relative text-sm text-text-muted/70 leading-relaxed">{item.description}</p>
              </motion.article>
            ))}
          </section>

          <motion.footer
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="pt-6 border-t border-white/[0.08] text-center pb-6"
          >
            <p className="text-[10px] text-text-muted/35 font-mono tracking-wide">
              ModelDoctor &middot; Team ASTROID &middot; Trustworthy ML from the start
            </p>
          </motion.footer>
        </main>
      </div>
    </div>
  );
}
