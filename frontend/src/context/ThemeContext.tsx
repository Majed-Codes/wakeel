import { createContext, useContext, useEffect, useState } from 'react'

interface ThemeContextType {
    isDark: boolean
    toggle: () => void
}

const ThemeContext = createContext<ThemeContextType>({
    isDark: true,
    toggle: () => {},
})

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [isDark, setIsDark] = useState<boolean>(() => {
        // Read saved preference; default to dark
        const saved = localStorage.getItem('wakeel_theme')
        return saved ? saved === 'dark' : true
    })

    useEffect(() => {
        const html = document.documentElement
        if (isDark) {
            html.classList.add('dark')
        } else {
            html.classList.remove('dark')
        }
        localStorage.setItem('wakeel_theme', isDark ? 'dark' : 'light')
    }, [isDark])

    return (
        <ThemeContext.Provider value={{ isDark, toggle: () => setIsDark(p => !p) }}>
            {children}
        </ThemeContext.Provider>
    )
}

export const useTheme = () => useContext(ThemeContext)
