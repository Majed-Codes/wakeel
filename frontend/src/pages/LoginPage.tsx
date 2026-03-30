import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Loader2 } from 'lucide-react'
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
        <div
            className="min-h-screen flex"
            style={{
                backgroundColor: '#000',
                backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)',
                backgroundSize: '28px 28px',
            }}
            dir="rtl"
        >
            {/* Left atmospheric panel — hidden on mobile */}
            <div
                className="hidden lg:flex flex-col justify-center px-16 xl:px-24"
                style={{ width: '55%', backgroundColor: '#000' }}
            >
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                >
                    <h2
                        style={{
                            fontFamily: "'Tajawal', sans-serif",
                            fontWeight: 200,
                            fontSize: 'clamp(2rem, 3.5vw, 3rem)',
                            lineHeight: 1.35,
                            color: 'rgba(255,255,255,0.92)',
                            marginBottom: '2.5rem',
                            letterSpacing: '0.01em',
                        }}
                    >
                        إدارة مالية دقيقة<br />للمنشآت السعودية
                    </h2>

                    <div className="space-y-3">
                        {[
                            'معدل الدقة ٩٥٪ — التعرف على اللهجة السعودية',
                            '١٧ وحدة تحليلية — في لوحة تحكم واحدة',
                            'امتثال كامل لمتطلبات زاتكا ٢٠٢٦',
                        ].map((stat, i) => (
                            <p
                                key={i}
                                style={{
                                    fontSize: '0.72rem',
                                    color: 'rgba(255,255,255,0.28)',
                                    letterSpacing: '0.02em',
                                    fontFamily: "'Tajawal', sans-serif",
                                }}
                            >
                                {stat}
                            </p>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* Right form panel */}
            <div
                className="flex flex-col justify-center w-full lg:w-auto px-8 sm:px-12 py-16"
                style={{ width: undefined, flexBasis: undefined, minWidth: 0, flex: '1 1 0', maxWidth: '100%', backgroundColor: '#0d0d0d' }}
            >
                <div className="w-full max-w-sm mx-auto" style={{ maxWidth: '360px' }}>
                    <motion.div
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.55, ease: 'easeOut' }}
                    >
                        {/* Form heading */}
                        <div className="mb-10">
                            <h1
                                style={{
                                    fontFamily: "'Tajawal', sans-serif",
                                    fontWeight: 500,
                                    fontSize: '1.35rem',
                                    color: 'rgba(255,255,255,0.9)',
                                    marginBottom: '0.35rem',
                                }}
                            >
                                {isRegister ? 'إنشاء حساب جديد' : 'تسجيل الدخول'}
                            </h1>
                            <p style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.3)' }}>
                                {isRegister ? 'أدخل بيانات منشأتك للبدء' : 'أدخل بيانات حسابك للمتابعة'}
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-7">
                            <AnimatePresence mode="wait">
                                {isRegister && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="overflow-hidden"
                                    >
                                        <div className="pb-1">
                                            <label
                                                style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', display: 'block', marginBottom: '0.5rem' }}
                                            >
                                                اسم المنشأة
                                            </label>
                                            <input
                                                type="text"
                                                required={isRegister}
                                                value={form.name}
                                                onChange={e => setForm({ ...form, name: e.target.value })}
                                                placeholder="مقهى المساء"
                                                style={{
                                                    width: '100%',
                                                    background: 'transparent',
                                                    border: 'none',
                                                    borderBottom: '1px solid rgba(255,255,255,0.15)',
                                                    color: '#fff',
                                                    fontSize: '0.9rem',
                                                    padding: '0.4rem 0',
                                                    outline: 'none',
                                                    fontFamily: "'Tajawal', sans-serif",
                                                }}
                                                onFocus={e => (e.target.style.borderBottomColor = 'rgba(255,255,255,0.45)')}
                                                onBlur={e => (e.target.style.borderBottomColor = 'rgba(255,255,255,0.15)')}
                                            />
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <div>
                                <label
                                    style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', display: 'block', marginBottom: '0.5rem' }}
                                >
                                    رقم الجوال
                                </label>
                                <input
                                    type="tel"
                                    required
                                    value={form.phone}
                                    onChange={e => setForm({ ...form, phone: e.target.value })}
                                    dir="ltr"
                                    placeholder="05XXXXXXXX"
                                    style={{
                                        width: '100%',
                                        background: 'transparent',
                                        border: 'none',
                                        borderBottom: '1px solid rgba(255,255,255,0.15)',
                                        color: '#fff',
                                        fontSize: '0.9rem',
                                        padding: '0.4rem 0',
                                        outline: 'none',
                                        textAlign: 'right',
                                        fontFamily: "'Tajawal', sans-serif",
                                    }}
                                    onFocus={e => (e.target.style.borderBottomColor = 'rgba(255,255,255,0.45)')}
                                    onBlur={e => (e.target.style.borderBottomColor = 'rgba(255,255,255,0.15)')}
                                />
                            </div>

                            <div>
                                <label
                                    style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.35)', display: 'block', marginBottom: '0.5rem' }}
                                >
                                    كلمة المرور
                                </label>
                                <input
                                    type="password"
                                    required
                                    value={form.password}
                                    onChange={e => setForm({ ...form, password: e.target.value })}
                                    dir="ltr"
                                    placeholder="••••••••"
                                    style={{
                                        width: '100%',
                                        background: 'transparent',
                                        border: 'none',
                                        borderBottom: '1px solid rgba(255,255,255,0.15)',
                                        color: '#fff',
                                        fontSize: '0.9rem',
                                        padding: '0.4rem 0',
                                        outline: 'none',
                                        textAlign: 'right',
                                        fontFamily: "'Tajawal', sans-serif",
                                    }}
                                    onFocus={e => (e.target.style.borderBottomColor = 'rgba(255,255,255,0.45)')}
                                    onBlur={e => (e.target.style.borderBottomColor = 'rgba(255,255,255,0.15)')}
                                />
                            </div>

                            {error && (
                                <motion.p
                                    initial={{ opacity: 0, y: -4 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    style={{ fontSize: '0.75rem', color: '#f87171', margin: 0 }}
                                >
                                    {error}
                                </motion.p>
                            )}

                            <button
                                type="submit"
                                disabled={loading}
                                style={{
                                    width: '100%',
                                    padding: '0.75rem 0',
                                    backgroundColor: '#2F80ED',
                                    color: '#fff',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontSize: '0.875rem',
                                    fontWeight: 500,
                                    fontFamily: "'Tajawal', sans-serif",
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    opacity: loading ? 0.7 : 1,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.5rem',
                                    marginTop: '0.5rem',
                                }}
                            >
                                {loading
                                    ? <Loader2 className="w-4 h-4 animate-spin" />
                                    : (isRegister ? 'إنشاء حساب' : 'دخول')
                                }
                            </button>
                        </form>

                        <div className="mt-8 text-center">
                            <button
                                onClick={() => { setIsRegister(!isRegister); setError('') }}
                                style={{
                                    fontSize: '0.72rem',
                                    color: 'rgba(255,255,255,0.3)',
                                    background: 'none',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontFamily: "'Tajawal', sans-serif",
                                }}
                                onMouseEnter={e => ((e.target as HTMLElement).style.color = 'rgba(255,255,255,0.6)')}
                                onMouseLeave={e => ((e.target as HTMLElement).style.color = 'rgba(255,255,255,0.3)')}
                            >
                                {isRegister ? 'لديك حساب مسجل؟ دخول' : 'ليس لديك حساب؟ إنشاء حساب جديد'}
                            </button>
                        </div>
                    </motion.div>
                </div>
            </div>
        </div>
    )
}
