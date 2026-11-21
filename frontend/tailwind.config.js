/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        claudio: {
          DEFAULT: "#1e3a5f",
          light: "#2d5a8c",
          accent: "#c9a84c",
        },
      },
    },
  },
  plugins: [],
};
