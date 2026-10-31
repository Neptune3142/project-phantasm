/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        phantom: {
          bg:        '#0B0710',  // deep charcoal
          panel:     '#140F1B',  // raised panel
          panel2:    '#1B1424',  // hover
          border:    '#2A1F3C',  // panel border
          purple:    '#7C3AED',  // deep purple accent
          purpleBri: '#A855F7',  // bright purple
          green:     '#22C55E',  // neon operational
          greenBri:  '#4ADE80',
          amber:     '#F59E0B',
          red:       '#EF4444',  // critical
          redBri:    '#F87171',
          text:      '#E6E1F0',
          textDim:   '#9A8DB0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'glow-purple': '0 0 0 1px rgba(124, 58, 237, 0.4), 0 0 24px rgba(124, 58, 237, 0.25)',
        'glow-green':  '0 0 0 1px rgba(34, 197, 94, 0.4), 0 0 24px rgba(34, 197, 94, 0.25)',
        'glow-red':    '0 0 0 1px rgba(239, 68, 68, 0.4), 0 0 24px rgba(239, 68, 68, 0.25)',
        'glow-amber':  '0 0 0 1px rgba(245, 158, 11, 0.4), 0 0 24px rgba(245, 158, 11, 0.25)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'flicker':    'flicker 3s linear infinite',
        'float':      'float 6s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 12px rgba(34, 197, 94, 0.4)' },
          '50%':      { boxShadow: '0 0 24px rgba(34, 197, 94, 0.7)' },
        },
        flicker: {
          '0%, 19%, 21%, 23%, 25%, 54%, 56%, 100%': { opacity: '1' },
          '20%, 22%, 24%, 55%': { opacity: '0.4' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-6px)' },
        },
      },
    },
  },
  plugins: [],
};
