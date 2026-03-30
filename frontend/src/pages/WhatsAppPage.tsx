import { useState, useEffect } from 'react'
import { MessageCircle, Phone, CheckCircle, XCircle, Send, Wifi, WifiOff, AlertCircle, Loader } from 'lucide-react'
import { motion } from 'framer-motion'
import { whatsappAPI } from '../api'

const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.08 } },
}
const item = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0 },
}

interface WhatsAppStatus {
    configured: boolean
    business_id: number
    features: Record<string, boolean>
    message: string
}

interface WeeklySummary {
    summary: string
}

export default function WhatsAppPage() {
    const [status, setStatus] = useState<WhatsAppStatus | null>(null)
    const [loading, setLoading] = useState(true)
    const [phoneNumber, setPhoneNumber] = useState('')
    const [connecting, setConnecting] = useState(false)
    const [connected, setConnected] = useState(false)
    const [testMsg, setTestMsg] = useState('')
    const [sendingTest, setSendingTest] = useState(false)
    const [weeklySummary, setWeeklySummary] = useState<string>('')
    const [loadingSummary, setLoadingSummary] = useState(false)

    useEffect(() => {
        loadStatus()
    }, [])

    const loadStatus = async () => {
        setLoading(true)
        try {
            const res = await whatsappAPI.status()
            setStatus(res.data)
        } catch {
            // error
        } finally {
            setLoading(false)
        }
    }

    const handleConnect = async () => {
        if (!phoneNumber.trim()) return
        setConnecting(true)
        try {
            await whatsappAPI.connect(phoneNumber)
            setConnected(true)
            setTimeout(() => setConnected(false), 3000)
        } catch {
            // error
        } finally {
            setConnecting(false)
        }
    }

    const handleSendTest = async () => {
        setSendingTest(true)
        try {
            await whatsappAPI.test(
                testMsg || 'مرحباً! هذه رسالة اختبار من وكيل AI.',
                phoneNumber || undefined
            )
            setTestMsg('')
        } catch {
            // error
        } finally {
            setSendingTest(false)
        }
    }

    const loadWeeklySummary = async () => {
        setLoadingSummary(true)
        try {
            const res = await whatsappAPI.weeklySummary()
            setWeeklySummary(res.data.summary)
        } catch {
            // error
        } finally {
            setLoadingSummary(false)
        }
    }

    const features = [
        { key: 'text_transactions', label: 'تسجيل المعاملات بالنص', desc: 'أرسل "دفعت 500 للمراعي" لتسجيل المعاملة تلقائياً' },
        { key: 'voice_transactions', label: 'تسجيل المعاملات بالصوت', desc: 'أرسل رسالة صوتية ليتم تفسيرها وتسجيلها' },
        { key: 'receipt_ocr', label: 'قراءة الإيصالات بالصورة', desc: 'صوّر إيصالك وأرسله للتسجيل التلقائي' },
        { key: 'financial_queries', label: 'استفسارات مالية', desc: 'اسأل عن وضعك المالي وتقاريرك' },
        { key: 'weekly_summary', label: 'ملخص أسبوعي', desc: 'استلم ملخصاً مالياً أسبوعياً كل يوم أحد' },
    ]

    return (
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
            {/* Header */}
            <motion.div variants={item} className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-success/20 flex items-center justify-center">
                    <MessageCircle className="w-6 h-6 text-success" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-heading">واتس اب بزنس</h1>
                    <p className="text-sm text-body mt-0.5">سجّل معاملاتك عبر واتساب بالنص والصوت والصورة</p>
                </div>
            </motion.div>

            {/* Connection Status */}
            {!loading && status && (
                <motion.div variants={item} className={`glass-card p-5 rounded-2xl border ${status.configured ? 'border-success/30' : 'border-warning/30'}`}>
                    <div className="flex items-center gap-3">
                        {status.configured
                            ? <Wifi className="w-5 h-5 text-success" />
                            : <WifiOff className="w-5 h-5 text-warning" />
                        }
                        <div>
                            <p className="font-semibold text-heading text-sm">
                                {status.configured ? 'متصل بواتس اب بزنس' : 'وضع المحاكاة'}
                            </p>
                            <p className="text-xs text-muted mt-0.5">{status.message}</p>
                        </div>
                    </div>
                </motion.div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Connect Phone */}
                <motion.div variants={item} className="glass-card p-6 rounded-2xl">
                    <h3 className="text-base font-bold text-heading mb-4 flex items-center gap-2">
                        <Phone className="w-4 h-4 text-accent" />
                        ربط رقم واتساب
                    </h3>
                    <div className="space-y-3">
                        <div>
                            <label className="text-xs text-muted mb-1.5 block">رقم الهاتف</label>
                            <input
                                type="tel"
                                placeholder="+966501234567"
                                value={phoneNumber}
                                onChange={e => setPhoneNumber(e.target.value)}
                                className="w-full bg-glass border border-glass-border rounded-xl px-4 py-2.5 text-heading text-sm placeholder:text-muted focus:outline-none focus:border-accent/50"
                                dir="ltr"
                            />
                        </div>
                        <button
                            onClick={handleConnect}
                            disabled={connecting || !phoneNumber}
                            className="w-full py-2.5 rounded-xl bg-accent text-white text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
                        >
                            {connecting
                                ? <><Loader className="w-4 h-4 animate-spin" /> جارٍ الربط...</>
                                : connected
                                    ? <><CheckCircle className="w-4 h-4" /> تم الربط بنجاح!</>
                                    : 'ربط الرقم'
                            }
                        </button>
                        <p className="text-xs text-muted text-center">
                            يجب أن يكون الرقم مرتبطاً بحساب واتساب نشط
                        </p>
                    </div>
                </motion.div>

                {/* Test Message */}
                <motion.div variants={item} className="glass-card p-6 rounded-2xl">
                    <h3 className="text-base font-bold text-heading mb-4 flex items-center gap-2">
                        <Send className="w-4 h-4 text-accent" />
                        إرسال رسالة اختبار
                    </h3>
                    <div className="space-y-3">
                        <div>
                            <label className="text-xs text-muted mb-1.5 block">الرسالة</label>
                            <textarea
                                placeholder="مرحباً! هذه رسالة اختبار من وكيل AI."
                                value={testMsg}
                                onChange={e => setTestMsg(e.target.value)}
                                rows={3}
                                className="w-full bg-glass border border-glass-border rounded-xl px-4 py-2.5 text-heading text-sm placeholder:text-muted focus:outline-none focus:border-accent/50 resize-none"
                            />
                        </div>
                        <button
                            onClick={handleSendTest}
                            disabled={sendingTest}
                            className="w-full py-2.5 rounded-xl bg-success/20 border border-success/30 text-success text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2 transition-all hover:bg-success/30"
                        >
                            {sendingTest
                                ? <><Loader className="w-4 h-4 animate-spin" /> جارٍ الإرسال...</>
                                : <><Send className="w-4 h-4" /> إرسال رسالة اختبار</>
                            }
                        </button>
                    </div>
                </motion.div>
            </div>

            {/* Features */}
            <motion.div variants={item} className="glass-card p-6 rounded-2xl">
                <h3 className="text-base font-bold text-heading mb-4 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-accent" />
                    المزايا المتاحة
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {features.map(f => {
                        const active = status?.features?.[f.key] ?? true
                        return (
                            <div key={f.key} className={`flex items-start gap-3 p-3 rounded-xl ${active ? 'bg-success/5 border border-success/20' : 'bg-glass border border-glass-border'}`}>
                                {active
                                    ? <CheckCircle className="w-4 h-4 text-success shrink-0 mt-0.5" />
                                    : <XCircle className="w-4 h-4 text-muted shrink-0 mt-0.5" />
                                }
                                <div>
                                    <p className="text-sm font-medium text-heading">{f.label}</p>
                                    <p className="text-xs text-muted mt-0.5">{f.desc}</p>
                                </div>
                            </div>
                        )
                    })}
                </div>
            </motion.div>

            {/* Weekly Summary Preview */}
            <motion.div variants={item} className="glass-card p-6 rounded-2xl">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-bold text-heading flex items-center gap-2">
                        <MessageCircle className="w-4 h-4 text-success" />
                        معاينة الملخص الأسبوعي
                    </h3>
                    <button
                        onClick={loadWeeklySummary}
                        disabled={loadingSummary}
                        className="text-xs text-accent hover:underline disabled:opacity-50"
                    >
                        {loadingSummary ? 'جارٍ التحميل...' : 'تحديث'}
                    </button>
                </div>
                {weeklySummary ? (
                    <div className="bg-success/5 border border-success/20 rounded-xl p-4">
                        <pre className="text-sm text-body whitespace-pre-wrap font-sans leading-relaxed">{weeklySummary}</pre>
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <MessageCircle className="w-10 h-10 text-muted mx-auto mb-2 opacity-40" />
                        <p className="text-sm text-muted">اضغط تحديث لمعاينة الملخص الأسبوعي</p>
                    </div>
                )}
            </motion.div>

            {/* Setup Instructions */}
            <motion.div variants={item} className="glass-card p-6 rounded-2xl">
                <h3 className="text-base font-bold text-heading mb-4">📋 تعليمات الإعداد</h3>
                <ol className="space-y-3 text-sm text-body">
                    <li className="flex gap-3">
                        <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold shrink-0">1</span>
                        <span>أنشئ حساباً على Twilio وفعّل واتس اب بزنس API</span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold shrink-0">2</span>
                        <span>أضف <code className="bg-glass px-1 rounded text-accent">TWILIO_ACCOUNT_SID</code> و <code className="bg-glass px-1 rounded text-accent">TWILIO_AUTH_TOKEN</code> و <code className="bg-glass px-1 rounded text-accent">TWILIO_WHATSAPP_NUMBER</code> في ملف <code className="bg-glass px-1 rounded text-accent">.env</code></span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold shrink-0">3</span>
                        <span>اضبط Webhook URL في لوحة Twilio على: <code className="bg-glass px-1 rounded text-accent dir-ltr">https://yourdomain.com/api/v1/whatsapp/webhook</code></span>
                    </li>
                    <li className="flex gap-3">
                        <span className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center text-xs font-bold shrink-0">4</span>
                        <span>أدخل رقمك واضغط "ربط الرقم" لبدء استخدام الخدمة</span>
                    </li>
                </ol>
            </motion.div>
        </motion.div>
    )
}
