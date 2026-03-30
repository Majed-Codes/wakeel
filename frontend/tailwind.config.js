/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'Tajawal', 'system-ui', 'sans-serif'],
                arabic: ['Tajawal', 'sans-serif'],
                mono: ['JetBrains Mono', 'SF Mono', 'monospace'],
            },
            colors: {
                // ── Theme-switching via CSS variables (light/dark) ──────────
                bg: 'var(--color-bg)',
                'bg-subtle': 'var(--color-bg-subtle)',
                glass: 'var(--color-glass)',
                'glass-border': 'var(--color-glass-border)',
                'glass-hover': 'var(--color-glass-hover)',
                'glass-active': 'var(--color-glass-active)',
                heading: 'var(--color-heading)',
                body: 'var(--color-body)',
                muted: 'var(--color-muted)',
                card: 'var(--color-card)',

                // ── Fixed accents — same in both themes ────────────────────
                accent: '#2F80ED',
                'accent-hover': '#1B6CDC',
                'accent-subtle': 'rgba(47, 128, 237, 0.1)',
                success: '#34C759',
                error: '#FF3B30',
                warning: '#FFCC00',
            },
            backgroundImage: {
                // CSS vars so light/dark can use different gradients
                'aurora': 'var(--bg-aurora)',
                'card-gradient': 'var(--bg-card-gradient)',
                'bento-gradient': 'var(--bg-bento-gradient)',
            },
            boxShadow: {
                'glass': 'var(--shadow-glass)',
                'glow': '0 0 20px rgba(47, 128, 237, 0.3)',
                'inner-light': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
            },
            borderRadius: {
                '2xl': '16px',
                '3xl': '24px',
            },
            animation: {
                'float': 'float 6s ease-in-out infinite',
                'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'gradient-x': 'gradient-x 15s ease infinite',
            },
            keyframes: {
                float: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-10px)' },
                },
                'gradient-x': {
                    '0%, 100%': {
                        'background-size': '200% 200%',
                        'background-position': 'left center'
                    },
                    '50%': {
                        'background-size': '200% 200%',
                        'background-position': 'right center'
                    },
                },
            },
        },
    },
    plugins: [],
}
