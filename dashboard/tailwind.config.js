/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        civic: {
          green: '#526B55',
          'green-dark': '#3B4E3D',
          'green-light': '#6E8B72',
          'green-container': '#E4ECE2',
          'on-green-container': '#111F13',
          bg: '#F7F7F2',
          surface: '#FFFFFF',
          border: '#E6E8E3',
          'border-subtle': '#EFEFEA',
          'text-primary': '#20231F',
          'text-secondary': '#5F6368',
          'text-muted': '#9AA0A6',
          // Dark palette tokens
          'dark-bg': '#121411',
          'dark-surface': '#1A1E1A',
          'dark-surface-elevated': '#222722',
          'dark-border': '#2E352D',
          'dark-text-primary': '#E2E5DF',
          'dark-text-secondary': '#9EA49D',
          'dark-text-muted': '#6B726A',
        },
        severity: {
          low: {
            text: '#1E8E3E',
            bg: '#E6F4EA',
            border: '#CEEAD6',
          },
          medium: {
            text: '#E37400',
            bg: '#FEF7E0',
            border: '#FEEFC3',
          },
          high: {
            text: '#D93025',
            bg: '#FCE8E6',
            border: '#FAD2CF',
          },
          critical: {
            text: '#B31412',
            bg: '#FAD2CF',
            border: '#F6AEA9',
          },
        },
        status: {
          intake: {
            text: '#4B5563',
            bg: '#F3F4F6',
            border: '#E5E7EB',
          },
          verification: {
            text: '#92400E',
            bg: '#FEF3C7',
            border: '#FDE68A',
          },
          workflow: {
            text: '#1E40AF',
            bg: '#EFF6FF',
            border: '#BFDBFE',
          },
          resolved: {
            text: '#065F46',
            bg: '#ECFDF5',
            border: '#A7F3D0',
          },
          closed: {
            text: '#374151',
            bg: '#E5E7EB',
            border: '#D1D5DB',
          },
        },
      },
      letterSpacing: {
        tighter: '-0.03em',
        tight: '-0.015em',
        normal: '0',
        wide: '0.025em',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        display: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
      boxShadow: {
        'civic-subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        'civic-card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        'civic-elevated': '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        'civic-modal': '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
      },
      borderRadius: {
        'civic': '0.625rem', // 10px Apple style rounded rect
        'civic-lg': '0.875rem', // 14px
      },
    },
  },
  plugins: [],
};
