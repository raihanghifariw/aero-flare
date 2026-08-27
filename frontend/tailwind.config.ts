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
        // Danger level colours matching plan/frontend_agent.md
        danger: {
          1: '#FEF08A',
          2: '#FCD34D',
          3: '#FB923C',
          4: '#EF4444',
          5: '#991B1B',
        },
      },
      animation: {
        spin: 'spin 1s linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;
