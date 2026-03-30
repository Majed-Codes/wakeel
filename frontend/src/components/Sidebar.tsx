import { useState } from 'react'
import {
    LayoutDashboard,
    Mic,
    MessageSquare,
    ShieldCheck,
    LogOut,
    Menu,
    X,
    TrendingUp,
    Upload,
    FileText,
    Bell,
    MessageCircle,
    PiggyBank,
    Star,
    Building2,
    Users,
    Sparkles,
    Sun,
    Moon,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useTheme } from '../context/ThemeContext'

interface SidebarProps {
    onLogout: () => void
}

const navItems = [
    { path: '/', label: 'الرئيسية', icon: LayoutDashboard },
    { path: '/voice', label: 'تسجيل', icon: Mic },
    { path: '/chat', label: 'المساعد', icon: MessageSquare },
    { path: '/advisor', label: 'المستشار', icon: Sparkles },
    { path: '/forecast', label: 'التنبؤ', icon: TrendingUp },
    { path: '/budget', label: 'الميزانية', icon: PiggyBank },
    { path: '/upload', label: 'استيراد', icon: Upload },
    { path: '/vendors', label: 'الموردون', icon: Building2 },
    { path: '/payroll', label: 'الرواتب', icon: Users },
    { path: '/reports', label: 'التقارير', icon: FileText },
    { path: '/alerts', label: 'التنبيهات', icon: Bell },
    { path: '/zakat', label: 'الزكاة', icon: Star },
    { path: '/whatsapp', label: 'واتس اب بزنس', icon: MessageCircle },
    { path: '/compliance', label: 'الامتثال', icon: ShieldCheck },
]

export default function Sidebar({ onLogout }: SidebarProps) {
    const [isOpen, setIsOpen] = useState(false)
    const { isDark, toggle } = useTheme()

    return (
        <>
            {/* Mobile Menu Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="lg:hidden fixed top-5 right-5 z-50 p-2.5 bg-glass backdrop-blur-md rounded-xl border border-glass-border text-heading shadow-glass"
            >
                {isOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            {/* Desktop Floating Dock */}
            <aside className="
                hidden lg:flex fixed z-40
                right-4 top-4 bottom-4 w-[72px] rounded-2xl
                flex-col items-center py-6
                bg-glass backdrop-blur-2xl border border-glass-border shadow-glass
            ">
                {/* Logo */}
                <div className="mb-6">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-glow">
                        <span className="text-white font-bold text-lg">W</span>
                    </div>
                </div>

                {/* Nav Items — scrollable */}
                <nav className="flex-1 flex flex-col items-center gap-2 overflow-y-auto overflow-x-hidden w-full px-3 scrollbar-none">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            end={item.path === '/'}
                            className={({ isActive }) => `
                                relative group flex items-center justify-center
                                w-11 h-11 rounded-xl transition-all duration-200 flex-shrink-0
                                ${isActive ? 'bg-accent/20 text-white shadow-glow' : 'text-muted hover:text-heading hover:bg-glass-hover'}
                            `}
                        >
                            {({ isActive }) => (
                                <>
                                    <item.icon className={`w-5 h-5 transition-transform duration-200 ${isActive ? 'scale-110' : 'group-hover:scale-105'}`} />

                                    {/* Tooltip */}
                                    <div className="absolute right-14 top-1/2 -translate-y-1/2 px-3 py-1.5
                                                  bg-bg-subtle rounded-lg text-xs font-medium text-heading
                                                  opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0
                                                  transition-all duration-200 pointer-events-none whitespace-nowrap border border-glass-border shadow-glass">
                                        {item.label}
                                    </div>

                                    {/* Active indicator */}
                                    {isActive && (
                                        <motion.div
                                            layoutId="active-dot"
                                            className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-5 bg-accent rounded-full"
                                        />
                                    )}
                                </>
                            )}
                        </NavLink>
                    ))}
                </nav>

                {/* Theme Toggle */}
                <button
                    onClick={toggle}
                    className="w-11 h-11 rounded-xl flex items-center justify-center text-muted hover:text-heading hover:bg-glass-hover transition-colors mt-2"
                    title={isDark ? 'الوضع النهاري' : 'الوضع الليلي'}
                >
                    {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                </button>

                {/* Logout */}
                <button
                    onClick={onLogout}
                    className="w-11 h-11 rounded-xl flex items-center justify-center text-muted hover:text-error hover:bg-error/10 transition-colors mt-1"
                    title="تسجيل الخروج"
                >
                    <LogOut className="w-5 h-5" />
                </button>
            </aside>

            {/* Mobile Slide-over */}
            <AnimatePresence>
                {isOpen && (
                    <>
                        {/* Backdrop */}
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsOpen(false)}
                            className="fixed inset-0 bg-black/60 z-30 lg:hidden backdrop-blur-sm"
                        />

                        {/* Panel */}
                        <motion.aside
                            initial={{ x: '100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            className="
                                fixed inset-y-0 right-0 z-40 w-64 lg:hidden
                                flex flex-col py-8
                                bg-bg-subtle backdrop-blur-2xl border-l border-glass-border shadow-glass
                            "
                        >
                            {/* Logo + Theme */}
                            <div className="flex items-center justify-between px-5 mb-6">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-glow">
                                    <span className="text-white font-bold text-xl">W</span>
                                </div>
                                <button
                                    onClick={toggle}
                                    className="w-10 h-10 rounded-xl flex items-center justify-center text-muted hover:text-heading hover:bg-glass-hover transition-colors"
                                >
                                    {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                                </button>
                            </div>

                            {/* Nav Items */}
                            <nav className="flex-1 flex flex-col gap-1 w-full px-4 overflow-y-auto">
                                {navItems.map((item) => (
                                    <NavLink
                                        key={item.path}
                                        to={item.path}
                                        end={item.path === '/'}
                                        onClick={() => setIsOpen(false)}
                                        className={({ isActive }) => `
                                            flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200
                                            ${isActive ? 'bg-accent/20 text-accent' : 'text-muted hover:text-heading hover:bg-glass-hover'}
                                        `}
                                    >
                                        <item.icon className="w-5 h-5 flex-shrink-0" />
                                        <span className="font-medium text-sm">{item.label}</span>
                                    </NavLink>
                                ))}
                            </nav>

                            {/* Logout */}
                            <button
                                onClick={onLogout}
                                className="flex items-center gap-3 px-8 py-3 mt-4 text-muted hover:text-error transition-colors"
                            >
                                <LogOut className="w-5 h-5" />
                                <span className="font-medium text-sm">تسجيل الخروج</span>
                            </button>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </>
    )
}
