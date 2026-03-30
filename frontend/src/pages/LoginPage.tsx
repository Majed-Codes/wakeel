import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2, ArrowRight } from 'lucide-react'
import { authAPI } from '../api'

interface LoginPageProps {
    onLogin: () => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
    const [isRegister, setIsRegister] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [form, setForm] = useState({ name: '', phone: '', password: '' })

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            if (isRegister) {
                await authAPI.register({
                    name: form.name,
                    phone: form.phone,
                    password: form.password
                })
                setIsRegister(false)
                // Auto-fill for login
            } else {
                const res = await authAPI.login({
                    phone: form.phone,
                    password: form.password
                })
                localStorage.setItem('wakeel_token', res.data.access_token)
                onLogin()
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'حدث خطأ غير متوقع')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Aurora Background Mesh */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] -right-[10%] w-[500px] h-[500px] bg-accent/20 rounded-full blur-[100px] animate-float" />
                <div className="absolute bottom-[-10%] -left-[10%] w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[100px] animate-float" style={{ animationDelay: '2s' }} />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: "easeOut" }}
                className="w-full max-w-md bg-glass border border-glass-border shadow-glass rounded-3xl p-8 md:p-12 relative z-10 backdrop-blur-2xl"
            >
                {/* Header */}
                <div className="text-center mb-10">
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-purple-600 shadow-glow mb-6"
                    >
                        <span className="text-3xl font-bold text-white">W</span>
                    </motion.div>
                    <h1 className="text-3xl font-bold text-heading mb-2">وكيل الذكي</h1>
                    <p className="text-body text-sm">مستشارك المالي الرقمي</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                    <AnimatePresence mode="wait">
                        {isRegister && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="overflow-hidden"
                            >
                                <div className="space-y-1.5 mb-5">
                                    <label className="text-xs font-medium text-muted mr-1">اسم المنشأة</label>
                                    <input
                                        type="text"
                                        required={isRegister}
                                        value={form.name}
                                        onChange={e => setForm({ ...form, name: e.target.value })}
                                        className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-heading text-sm focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all"
                                        placeholder="مقهى المساء"
                                    />
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted mr-1">رقم الجوال</label>
                        <input
                            type="tel"
                            required
                            value={form.phone}
                            onChange={e => setForm({ ...form, phone: e.target.value })}
                            dir="ltr"
                            className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-heading text-sm focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all text-right placeholder:text-right"
                            placeholder="05XXXXXXXX"
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted mr-1">كلمة المرور</label>
                        <input
                            type="password"
                            required
                            value={form.password}
                            onChange={e => setForm({ ...form, password: e.target.value })}
                            dir="ltr"
                            className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-heading text-sm focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all text-right placeholder:text-right"
                            placeholder="••••••••"
                        />
                    </div>

                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="p-3 rounded-lg bg-error/10 border border-error/20 text-error text-xs text-center font-medium"
                        >
                            {error}
                        </motion.div>
                    )}

                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        type="submit"
                        disabled={loading}
                        className="w-full py-3.5 bg-accent hover:bg-accent-hover text-white rounded-xl font-semibold shadow-glow transition-all flex items-center justify-center gap-2 group"
                    >
                        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (
                            <>
                                {isRegister ? 'إنشاء حساب' : 'تسجيل الدخول'}
                                <ArrowRight className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                            </>
                        )}
                    </motion.button>
                </form>

                <div className="mt-8 text-center">
                    <button
                        onClick={() => { setIsRegister(!isRegister); setError('') }}
                        className="text-sm text-muted hover:text-white transition-colors"
                    >
                        {isRegister ? 'لديك حساب مسجل؟ دخول' : 'ليس لديك حساب؟ إنشاء حساب جديد'}
                    </button>
                </div>
            </motion.div>

            {/* Footer Credit */}
            <div className="absolute bottom-6 text-center w-full z-10">
                <p className="text-[10px] text-white/20 tracking-widest uppercase">Wakeel AI · v3.0</p>
            </div>
        </div>
    )
}
