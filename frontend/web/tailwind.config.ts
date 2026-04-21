import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "rgb(var(--background) / <alpha-value>)",
        "surface-low": "rgb(var(--surface-low) / <alpha-value>)",
        "surface-lowest": "rgb(var(--surface-lowest) / <alpha-value>)",
        "surface-high": "rgb(var(--surface-high) / <alpha-value>)",
        foreground: "rgb(var(--foreground) / <alpha-value>)",
        "muted-foreground": "rgb(var(--muted-foreground) / <alpha-value>)",
        primary: "rgb(var(--primary) / <alpha-value>)",
        "primary-strong": "rgb(var(--primary-strong) / <alpha-value>)",
        secondary: "rgb(var(--secondary) / <alpha-value>)",
        tertiary: "rgb(var(--tertiary) / <alpha-value>)",
        "tertiary-container": "rgb(var(--tertiary-container) / <alpha-value>)",
      },
      fontFamily: {
        body: ["var(--font-inter)", "system-ui", "sans-serif"],
        headline: ["var(--font-manrope)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        ambient: "0 4px 24px rgba(25, 28, 30, 0.06)",
      },
      keyframes: {
        pulseRing: {
          "0%": { transform: "scale(1)", opacity: "0.6" },
          "70%": { transform: "scale(1.08)", opacity: "0.1" },
          "100%": { transform: "scale(1.12)", opacity: "0" },
        },
      },
      animation: {
        "pulse-ring": "pulseRing 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
