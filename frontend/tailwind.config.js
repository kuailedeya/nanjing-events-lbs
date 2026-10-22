/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: '#007AFF',
          green: '#34C759',
          amber: '#FF9500',
          red: '#FF3B30',
          gray: '#8E8E93',
          card: '#F5F5F7',
          surface: '#FFFFFF',
          border: 'rgba(0,0,0,0.06)'
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'PingFang SC', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
