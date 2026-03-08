/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        void: '#05060b',
        surface: {
          DEFAULT: '#111631',
          dark: '#0c1021',
          deeper: '#080a14',
          elevated: '#161d3f',
        },
        accent: {
          DEFAULT: '#7c3aed',
          light: '#a78bfa',
          lighter: '#c4b5fd',
          dark: '#6d28d9',
          cyan: '#06b6d4',
          rose: '#f43f5e',
        },
        neon: {
          green: '#34d399',
          yellow: '#fbbf24',
          purple: '#a78bfa',
          red: '#fb7185',
          cyan: '#22d3ee',
          pink: '#c084fc',
        },
      },
      boxShadow: {
        glow: '0 0 20px rgba(124, 58, 237, 0.15)',
        'glow-lg': '0 0 40px rgba(124, 58, 237, 0.2)',
        'glow-cyan': '0 0 20px rgba(6, 182, 212, 0.15)',
        'glow-green': '0 0 20px rgba(16, 185, 129, 0.15)',
        'glow-rose': '0 0 20px rgba(244, 63, 94, 0.15)',
        'inner-glow': 'inset 0 1px 0 rgba(255, 255, 255, 0.04)',
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 3s ease-in-out infinite alternate',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(124, 58, 237, 0.15)' },
          '100%': { boxShadow: '0 0 25px rgba(124, 58, 237, 0.3)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'shimmer-gradient': 'linear-gradient(90deg, transparent, rgba(124, 58, 237, 0.08), transparent)',
      },
    },
  },
  plugins: [],
};
