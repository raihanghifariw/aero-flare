import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#F8FAFC', // soft slate canvas
          raised: '#FFFFFF', // crisp pure white floating cards & panels
          overlay: '#F1F5F9', // subtle hover / secondary pill container
          card: '#FFFFFF', // card containers
        },
        edge: {
          subtle: '#F1F5F9',
          DEFAULT: '#E2E8F0', // clean slate border
          strong: '#CBD5E1', // emphasized borders
          glow: 'rgba(24, 119, 242, 0.3)', // electric blue selection glow
        },
        ink: {
          DEFAULT: '#0F172A', // Slate 900 primary text
          muted: '#475569', // Slate 600 secondary text
          faint: '#94A3B8', // Slate 400 caption text
          inverse: '#FFFFFF', // White text on electric blue
        },
        brand: {
          DEFAULT: '#1877F2', // electric azure blue (from reference)
          soft: '#3B82F6',
          light: '#EFF6FF',
          dark: '#1D4ED8',
        },
        accent: {
          DEFAULT: '#1877F2', // primary electric blue
          soft: '#3B82F6',
          flame: '#FF5722',
          dim: '#EFF6FF',
          amber: '#F59E0B',
          cyan: '#0EA5E9',
          emerald: '#10B981',
          danger: '#EF4444',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        floating: '0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)',
        glow: '0 0 0 2px rgba(24, 119, 242, 0.25), 0 4px 14px rgba(24, 119, 242, 0.2)',
        tactical: '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 0 0 1px #E2E8F0',
        'glow-red': '0 0 0 2px rgba(239, 68, 68, 0.25), 0 4px 14px rgba(239, 68, 68, 0.2)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      animation: {
        'ping-slow': 'ping 2.5s cubic-bezier(0, 0, 0.2, 1) infinite',
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};

export default config;

