/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Core palette — dark industrial
        surface: {
          0:   '#08090a',  // deepest background
          1:   '#0f1012',  // page background
          2:   '#16181c',  // card / panel background
          3:   '#1e2127',  // elevated card
          4:   '#272b33',  // border default
          5:   '#333844',  // border hover
        },
        text: {
          1:   '#f0f2f5',  // primary text
          2:   '#9aa0ac',  // secondary text
          3:   '#5c6370',  // muted text
        },
        accent: {
          blue:   '#3b82f6',
          blueDim:'#1d4ed8',
          green:  '#22c55e',
          amber:  '#f59e0b',
          red:    '#ef4444',
          purple: '#a78bfa',
        },
        score: {
          high:   '#22c55e',  // 80+
          mid:    '#f59e0b',  // 60-79
          low:    '#ef4444',  // <60
        },
      },
      fontFamily: {
        sans:  ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono:  ['var(--font-geist-mono)', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
      borderRadius: {
        sm:  '2px',
        DEFAULT: '4px',
        md:  '6px',
        lg:  '8px',
      },
      animation: {
        'fade-in':   'fadeIn 0.2s ease-out',
        'slide-up':  'slideUp 0.25s ease-out',
        'pulse-dot': 'pulseDot 2s cubic-bezier(0.4,0,0.6,1) infinite',
      },
      keyframes: {
        fadeIn:   { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:  { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseDot: { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
      },
    },
  },
  plugins: [],
}
