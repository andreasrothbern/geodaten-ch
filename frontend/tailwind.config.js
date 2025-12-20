/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        swiss: {
          red: '#FF0000',
          white: '#FFFFFF',
        },
      },
    },
  },
  plugins: [],
}
