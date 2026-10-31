import type { Config } from "tailwindcss";

// Every colour reads a CSS variable defined in globals.css, so the whole
// app re-themes from ONE place. `<alpha-value>` lets bg-accent/10 work.
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: token("paper"),
        surface: token("surface"),
        ink: token("ink"),
        muted: token("muted"),
        line: token("line"),
        accent: token("accent"),
        "accent-soft": token("accent-soft"),
        warn: token("warn"),
        danger: token("danger"),
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        sans: ["var(--font-geist)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: { DEFAULT: "3px", sm: "2px", md: "4px", lg: "4px" },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pulseDot: {
          "0%,100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: ".45", transform: "scale(.7)" },
        },
      },
      animation: {
        shimmer: "shimmer 1.4s infinite",
        pulseDot: "pulseDot 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
