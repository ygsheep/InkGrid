import type { Config } from 'tailwindcss';

/**
 * Obsidian Spatial — Technical Minimalism design system.
 * Pure-black foundation, monochromatic palette, Geist + JetBrains Mono,
 * zero-radius geometry, 4px/8px modular spacing.
 */
const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Surface tier (pure-black OLED foundation)
        background: '#121414',
        surface: '#121414',
        'surface-dim': '#121414',
        'surface-bright': '#383939',
        'surface-container-lowest': '#0d0e0f',
        'surface-container-low': '#1b1c1c',
        'surface-container': '#1f2020',
        'surface-container-high': '#292a2a',
        'surface-container-highest': '#343535',
        'surface-variant': '#343535',

        // Text
        'on-surface': '#e3e2e2',
        'on-surface-variant': '#c4c7c8',
        'on-background': '#e3e2e2',

        // Inverse
        'inverse-surface': '#e3e2e2',
        'inverse-on-surface': '#303031',
        'inverse-primary': '#5d5f5f',

        // Outline
        outline: '#8e9192',
        'outline-variant': '#444748',

        // Primary (white)
        primary: '#ffffff',
        'on-primary': '#2f3131',
        'primary-container': '#e2e2e2',
        'on-primary-container': '#636565',
        'primary-fixed': '#e2e2e2',
        'primary-fixed-dim': '#c6c6c7',
        'on-primary-fixed': '#1a1c1c',
        'on-primary-fixed-variant': '#454747',
        'surface-tint': '#c6c6c7',

        // Secondary
        secondary: '#c8c6c5',
        'on-secondary': '#313030',
        'secondary-container': '#474746',
        'on-secondary-container': '#b7b5b4',
        'secondary-fixed': '#e5e2e1',
        'secondary-fixed-dim': '#c8c6c5',
        'on-secondary-fixed': '#1c1b1b',
        'on-secondary-fixed-variant': '#474746',

        // Tertiary (functional green accent)
        tertiary: '#ffffff',
        'on-tertiary': '#003919',
        'tertiary-container': '#6bfe9c',
        'on-tertiary-container': '#00743a',
        'tertiary-fixed': '#6bfe9c',
        'tertiary-fixed-dim': '#4ae183',
        'on-tertiary-fixed': '#00210c',
        'on-tertiary-fixed-variant': '#005228',

        // Error
        error: '#ffb4ab',
        'on-error': '#690005',
        'error-container': '#93000a',
        'on-error-container': '#ffdad6',
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'Inter', 'system-ui', 'sans-serif'],
        headline: ['var(--font-geist-sans)', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        // Display / Headlines (Geist)
        'headline-lg': ['48px', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '600' }],
        'headline-lg-mobile': ['32px', { lineHeight: '1.2', letterSpacing: '-0.01em', fontWeight: '600' }],
        'headline-md': ['24px', { lineHeight: '1.4', letterSpacing: '-0.01em', fontWeight: '500' }],
        // Body
        'body-md': ['16px', { lineHeight: '1.6', letterSpacing: '0', fontWeight: '400' }],
        'body-sm': ['14px', { lineHeight: '1.5', fontWeight: '400' }],
        // Technical labels
        'label-mono': ['12px', { lineHeight: '1', letterSpacing: '0.05em', fontWeight: '500' }],
      },
      spacing: {
        base: '4px',
        'grid-minor': '8px',
        'grid-major': '32px',
        gutter: '24px',
        'margin-mobile': '16px',
        'margin-desktop': '48px',
      },
      // Zero-radius geometry — engineered aesthetic
      borderRadius: {
        none: '0px',
        sm: '0px',
        DEFAULT: '0px',
        md: '0px',
        lg: '0px',
        xl: '0px',
        full: '9999px',
      },
      maxWidth: {
        article: '720px',
        list: '1100px',
        chat: '880px',
        admin: '1200px',
        'page-7xl': '1280px',
      },
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
      },
    },
  },
  plugins: [],
};

export default config;
