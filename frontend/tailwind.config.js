/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Space Grotesk', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        background: '#020204',
        foreground: '#EDEDED',
        card: {
          DEFAULT: '#0A0A0B',
          foreground: '#FFFFFF',
        },
        popover: {
          DEFAULT: '#050505',
          foreground: '#EDEDED',
        },
        primary: {
          DEFAULT: '#00FF94',
          foreground: '#000000',
        },
        secondary: {
          DEFAULT: '#1A1A1D',
          foreground: '#FFFFFF',
        },
        muted: {
          DEFAULT: '#1A1A1D',
          foreground: '#A1A1AA',
        },
        accent: {
          DEFAULT: '#28282D',
          foreground: '#00FF94',
        },
        destructive: {
          DEFAULT: '#FF003D',
          foreground: '#FFFFFF',
        },
        border: '#27272A',
        input: '#27272A',
        ring: '#00FF94',
      },
      borderRadius: {
        lg: '0.75rem',
        md: '0.5rem',
        sm: '0.25rem',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}