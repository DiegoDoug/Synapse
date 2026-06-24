/** @type {import('tailwindcss').Config} */
export default {
  // Dark mode first: toggled via a `dark` class on <html>.
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
