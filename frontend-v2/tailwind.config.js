/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f6ff',
          100: '#d9e6ff',
          200: '#b2cdff',
          300: '#7fa8ff',
          400: '#4d82ff',
          500: '#1f5cff',
          600: '#0b39d9',
          700: '#0a2ea8',
          800: '#0a2d7f',
          900: '#0b275f',
        },
      },
    },
  },
  plugins: [],
};
