/** @type {import('tailwindcss').Config} */

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        navy: "#101827",
        accent: "#6366F1",
        surface: "#F8FAFC"
      }
    }
  },
  plugins: []
};