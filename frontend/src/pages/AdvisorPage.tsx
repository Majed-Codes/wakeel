import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, RefreshCw, CheckCircle2, Circle } from 'lucide-react'
import { advisorAPI } from '../api'

interface AdvisorInsights {
    weekly_advice: string
    focus_areas: string[]
    action_items: string[]
    health_score: number
    generated_at: string
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

function HealthGauge({ score }: { score: number }) {
    const radius = 54
    const circ = 2 * Math.PI * radius
    const progress = (score / 100) * circ * 0.75   // 270° arc
    const color = score >= 70 ? '#34C759' : score >= 40 ? '#FFCC00' : '#FF3B30'

    return (
        <div className="relative w-40 h-40 mx-auto">
            <svg className="w-full h-full -rotate-[135deg]" viewBox="0 0 128 128">
                <circle cx="64" cy="64" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12"
                    strokeDasharray={`${circ * 0.75} ${circ}`} strokeLinecap="round" />
                <motion.circle cx="64" cy="64" r={radius} fill="none" stroke={color} strokeWidth="12"
                    strokeLinecap="round"
                    initial={{ strokeDasharray: `0 ${circ}` }}
                    animate={{ strokeDasharray: `${progress} ${circ}` }}
                    transition={{ duration: 1.2, ease: 'easeOut' }} />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-heading tabular-nums">{score}</span>
                <span className="text-xs text-muted">/ 100</span>
            </div>
        </div>
    )
}

export default function AdvisorPage() {
    const [data, setData] = useState<AdvisorInsights | null>(null)
    const [loading, setLoading] = useState(true)
    const [checked, setChecked] = useState<Set<number>>(new Set())

    const load = () => {
        setLoading(true)
        setChecked(new Set())
        advisorAPI.get()
            .then(r => setData(r.data))
            .catch(() => setData(null))
            .finally(() => setLoading(false))
    }

    useEffect(() => { load() }, [])

    const toggleCheck = (i: number) => {
        setChecked(prev => {
            const next = new Set(prev)
            if (next.has(i)) next.delete(i)
            else next.add(i)
            return next
        })
    }

    const healthLabel = (s: number) => s >= 70 ? 'ممتاز' : s >= 40 ? 'متوسط' : 'يحتاج اهتمام'
    const healthColor = (s: number) => s >= 70 ? 'text-success' : s >= 40 ? 'text-warning' : 'text-error'

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-heading flex items-center gap-3">
                        <Sparkles className="text-accent" size={32} /> وكيلك المالي الذكي
                    </h1>
                    <p className="text-body mt-1">نصائح مالية شخصية مدعومة بالذكاء الاصطناعي</p>
                </div>
                <button
                    onClick={load}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-glass border border-glass-border rounded-xl text-sm text-heading hover:bg-glass-hover transition-colors"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> تحديث النصائح
                </button>
            </div>

            {loading ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4">
                    <Sparkles size={40} className="text-accent animate-pulse" />
                    <p className="text-muted">يحلل وكيلك وضعك المالي...</p>
                </div>
            ) : !data ? (
                <div className="flex flex-col items-center justify-center h-64 text-center">
                    <Sparkles size={48} className="text-muted mb-3" />
                    <p className="text-muted">تعذّر توليد النصائح</p>
                    <p className="text-muted text-sm mt-1">تأكد من وجود معاملات مسجّلة</p>
                </div>
            ) : (
                <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
                    {/* Health Score + Advice — side by side on desktop */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Health Gauge */}
                        <motion.div variants={item} className="glass-panel rounded-3xl p-6 flex flex-col items-center justify-center">
                            <p className="text-sm font-medium text-muted mb-4">مؤشر الصحة المالية</p>
                            <HealthGauge score={data.health_score} />
                            <p className={`mt-3 font-bold text-lg ${healthColor(data.health_score)}`}>
                                {healthLabel(data.health_score)}
                            </p>
                        </motion.div>

                        {/* Weekly Advice */}
                        <motion.div variants={item} className="md:col-span-2 glass-panel rounded-3xl p-6">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="w-7 h-7 rounded-full bg-accent/20 flex items-center justify-center">
                                    <Sparkles size={14} className="text-accent" />
                                </div>
                                <h3 className="font-semibold text-heading">النصيحة الأسبوعية</h3>
                            </div>
                            <p className="text-body leading-relaxed text-[15px]">{data.weekly_advice}</p>
                            {data.generated_at && (
                                <p className="text-xs text-muted mt-4">
                                    تم التوليد: {new Date(data.generated_at).toLocaleDateString('ar-SA')}
                                </p>
                            )}
                        </motion.div>
                    </div>

                    {/* Focus Areas */}
                    {data.focus_areas?.length > 0 && (
                        <motion.div variants={item} className="glass-panel rounded-3xl p-6">
                            <h3 className="font-semibold text-heading mb-4">مجالات التركيز</h3>
                            <div className="flex flex-wrap gap-3">
                                {data.focus_areas.map((f, i) => (
                                    <motion.span
                                        key={i}
                                        initial={{ opacity: 0, scale: 0.9 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: i * 0.1 }}
                                        className="px-4 py-2 rounded-full bg-accent/10 border border-accent/20 text-accent text-sm font-medium"
                                    >
                                        {f}
                                    </motion.span>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {/* Action Items — interactive checklist */}
                    {data.action_items?.length > 0 && (
                        <motion.div variants={item} className="glass-panel rounded-3xl p-6">
                            <h3 className="font-semibold text-heading mb-4">الإجراءات الموصى بها</h3>
                            <div className="space-y-3">
                                {data.action_items.map((action, i) => (
                                    <motion.button
                                        key={i}
                                        onClick={() => toggleCheck(i)}
                                        className="w-full flex items-start gap-3 text-right hover:bg-glass-hover transition-colors rounded-xl p-3"
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.1 }}
                                    >
                                        {checked.has(i)
                                            ? <CheckCircle2 size={20} className="text-success flex-shrink-0 mt-0.5" />
                                            : <Circle size={20} className="text-muted flex-shrink-0 mt-0.5" />
                                        }
                                        <span className={`text-sm text-right ${checked.has(i) ? 'line-through text-muted' : 'text-body'}`}>
                                            {action}
                                        </span>
                                    </motion.button>
                                ))}
                            </div>
                            {checked.size === data.action_items.length && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="mt-4 p-3 bg-success/10 rounded-xl text-center text-success text-sm font-medium"
                                >
                                    أحسنت! أتممت جميع الإجراءات 🎉
                                </motion.div>
                            )}
                        </motion.div>
                    )}
                </motion.div>
            )}
        </div>
    )
}
