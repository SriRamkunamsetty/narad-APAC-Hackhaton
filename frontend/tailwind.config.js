/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        void:      "#05070A",
        surface:   "#0B0F14",
        panel:     "#10161D",
        line:      "#1C2530",
        signal:    "#00E5A0",
        signal2:   "#00B8FF",
        warn:      "#FFB020",
        crit:      "#FF3B5C",
        muted:     "#5C6B7A",
        ink:       "#E8EDF2",
        inkdim:    "#9AACBC",
      },
      fontFamily: {
        display: ["'JetBrains Mono'", "monospace"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px -4px rgba(0,229,160,0.35)",
        glowBlue: "0 0 24px -4px rgba(0,184,255,0.35)",
        glowCrit: "0 0 24px -4px rgba(255,59,92,0.4)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        scan: "scan 3s linear infinite",
      },
      keyframes: {
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        }
      }
    },
  },
  plugins: [],
}
