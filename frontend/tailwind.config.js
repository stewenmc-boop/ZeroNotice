/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0b0f",
        muted: "#6f6f78",
        faint: "#a1a1aa",
        line: "#ededf0",
        canvas: "#fafafa",
        accent: { DEFAULT: "#18181b", soft: "#f4f4f5" },
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "Inter",
          "Noto Sans KR",
          "Noto Sans SC",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      fontSize: {
        meta: ["11px", { lineHeight: "16px" }],
        label: ["12px", { lineHeight: "16px" }],
        body: ["13px", { lineHeight: "20px" }],
        title: ["14px", { lineHeight: "20px" }],
        h3: ["16px", { lineHeight: "24px" }],
        h1: ["20px", { lineHeight: "28px" }],
      },
      borderRadius: {
        card: "14px",
        control: "10px",
        chip: "8px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,24,40,0.04)",
        pop: "0 10px 30px -12px rgba(16,24,40,0.22)",
      },
    },
  },
  plugins: [],
};
