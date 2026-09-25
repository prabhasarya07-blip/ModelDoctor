/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        void: "#0A0A14",
        surface: "#12121F",
        border: "#1E1E35",
        "accent-blue": "#4285F4",
        "accent-teal": "#00DEB4",
        "accent-red": "#FF2244",
        "accent-orange": "#FF5500",
        "accent-yellow": "#FFB800",
        "accent-purple": "#A855F7",
        "accent-green": "#00C896",
        "text-primary": "#E8E8FF",
        "text-muted": "#6B6B8A",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "-apple-system", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "drift-1": "drift-1 20s ease-in-out infinite",
        "drift-2": "drift-2 25s ease-in-out infinite",
        "drift-3": "drift-3 18s ease-in-out infinite",
        "pulse-dot": "pulse-dot 2s ease-in-out infinite",
        shimmer: "shimmer 3s ease-in-out infinite",
        "border-rotate": "border-rotate 4s linear infinite",
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
