"use client";

import { motion, useReducedMotion } from "framer-motion";

const SIGNAL_CARDS = [
  {
    title: "Pipeline Data Flow",
    subtitle: "Input -> Features -> Model -> Eval",
    kind: "flow",
  },
  {
    title: "Training Heartbeat",
    subtitle: "Live stability pulse",
    kind: "heartbeat",
  },
  {
    title: "Confidence Radar",
    subtitle: "Generalization monitor",
    kind: "radar",
  },
] as const;

export default function MLSignalsShowcase() {
  const shouldReduceMotion = useReducedMotion();

  return (
    <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {SIGNAL_CARDS.map((card, index) => (
        <motion.article
          key={card.title}
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.45, delay: index * 0.08 }}
          whileHover={shouldReduceMotion ? undefined : { y: -4, scale: 1.01 }}
          className="glass rounded-2xl p-4 border border-white/10 relative overflow-hidden"
        >
          <p className="text-[10px] uppercase tracking-[0.14em] text-accent-blue/75 mb-2">ML Signal {index + 1}</p>
          <h3 className="text-sm font-semibold text-text-primary">{card.title}</h3>
          <p className="text-xs text-text-muted/70 mt-1">{card.subtitle}</p>

          {card.kind === "flow" && (
            <div className="ml-flow-track mt-4">
              <div className="ml-flow-line" />
              <span className="ml-flow-node ml-flow-node-a">IN</span>
              <span className="ml-flow-node ml-flow-node-b">FT</span>
              <span className="ml-flow-node ml-flow-node-c">MD</span>
              <span className="ml-flow-node ml-flow-node-d">EV</span>
              <div className="ml-flow-packet" />
            </div>
          )}

          {card.kind === "heartbeat" && (
            <div className="ml-heartbeat-bars mt-4">
              {Array.from({ length: 18 }).map((_, barIndex) => (
                <span
                  key={barIndex}
                  className="ml-heartbeat-bar"
                  style={{ animationDelay: `${barIndex * 0.08}s` }}
                />
              ))}
            </div>
          )}

          {card.kind === "radar" && (
            <div className="ml-radar mt-4">
              <div className="ml-radar-ring ml-radar-ring-1" />
              <div className="ml-radar-ring ml-radar-ring-2" />
              <div className="ml-radar-ring ml-radar-ring-3" />
              <div className="ml-radar-sweep" />
              <span className="ml-radar-dot ml-radar-dot-a" />
              <span className="ml-radar-dot ml-radar-dot-b" />
              <span className="ml-radar-dot ml-radar-dot-c" />
            </div>
          )}
        </motion.article>
      ))}
    </section>
  );
}
