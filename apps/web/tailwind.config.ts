import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#11151c",
        border: "#1f2430",
        accent: "#5ccfe6",
        positive: "#4ade80",
        negative: "#f87171",
      },
    },
  },
  plugins: [],
};

export default config;
