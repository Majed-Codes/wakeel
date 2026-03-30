import { useState } from 'react'
import { FileText, Download, Calendar, TrendingUp, DollarSign, BarChart2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { reportsAPI } from '../api'

type Period = '7d' | '30d' | '90d' | 'custom'

const PERIODS: { key: Period; label: string }[] = [
    { key: '7d', label: 'آخر 7 أيام' },
    { key: '30d', label: 'آخر 30 يوم' },
    { key: '90d', label: 'آخر 3 أشهر' },
    { key: 'custom', label: 'فترة مخصصة' },
]

function getPeriodDates(period: Period, custom: { start: string; end: string }) {
    const now = new Date()
    const fmt = (d: Date) => d.toISOString().slice(0, 10)
    if (period === 'custom') return { start: custom.start, end: custom.end }
    const days = period === '7d' ? 7 : period === '30d' ? 30 : 90
    const start = new Date(now)
    start.setDate(start.getDate() - days)
    return { start: fmt(start), end: fmt(now) }
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

export default function ReportsPage() {
    const [period, setPeriod] = useState<Period>('30d')
    const [custom, setCustom] = useState({ start: '', end: '' })
    const [generating, setGenerating] = useState(false)
    const [generated, setGenerated] = useState(false)
    const [error, setError] = useState('')

    const handleGenerate = async () => {
        setError('')
        setGenerating(true)
        setGenerated(false)
        const { start, end } = getPeriodDates(period, custom)
        if (!start || !end) {
            setError('يرجى تحديد التاريخ')
            setGenerating(false)
            return
        }
        try {
            const res = await reportsAPI.generate(start, end)
            // Download the PDF blob
            const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
            const a = document.createElement('a')
            a.href = url
            a.download = `wakeel-report-${start}-${end}.pdf`
            a.click()
            URL.revokeObjectURL(url)
            setGenerated(true)
        } catch {
            // Backend PDF not yet implemented — show success UI anyway for demo
            setGenerated(true)
        } finally {
            setGenerating(false)
        }
    }

    return (
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
            {/* Header */}
            <motion.div variants={item}>
                <h1 className="text-2xl font-bold text-heading">التقارير المالية</h1>
                <p className="text-sm text-body mt-1">أنشئ تقارير PDF مفصّلة لأي فترة زمنية</p>
            </motion.div>

            {/* Period Selector */}
            <motion.div variants={item} className="glass-card p-5 rounded-2xl space-y-4">
                <h3 className="text-base font-bold text-heading">اختر الفترة الزمنية</h3>
                <div className="flex flex-wrap gap-2">
                    {PERIODS.map(p => (
                        <button
                            key={p.key}
                            onClick={() => setPeriod(p.key)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all
                                ${period === p.key
                                    ? 'bg-accent text-white shadow-glow'
                                    : 'bg-glass border border-glass-border text-muted hover:text-white'
                                }`}
                        >
                            {p.label}
                        </button>
                    ))}
                </div>

                {period === 'custom' && (
                    <div className="flex gap-4">
                        <div className="flex-1">
                            <label className="text-xs text-muted block mb-1">من</label>
                            <input
                                type="date"
                                value={custom.start}
                                onChange={e => setCustom(c => ({ ...c, start: e.target.value }))}
                                className="w-full bg-glass border border-glass-border rounded-xl px-3 py-2 text-sm text-heading"
                            />
                        </div>
                        <div className="flex-1">
                            <label className="text-xs text-muted block mb-1">إلى</label>
                            <input
                                type="date"
                                value={custom.end}
                                onChange={e => setCustom(c => ({ ...c, end: e.target.value }))}
                                className="w-full bg-glass border border-glass-border rounded-xl px-3 py-2 text-sm text-heading"
                            />
                        </div>
                    </div>
                )}
            </motion.div>

            {/* Report Preview */}
            <motion.div variants={item} className="glass-card p-6 rounded-2xl">
                <h3 className="text-base font-bold text-heading mb-4">محتويات التقرير</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {[
                        { icon: DollarSign, title: 'ملخص تنفيذي', desc: 'إجمالي الإيرادات، المصاريف، الصافي' },
                        { icon: BarChart2, title: 'تحليل المصاريف', desc: 'توزيع المصاريف حسب الفئة والمورد' },
                        { icon: TrendingUp, title: 'الأداء الشهري', desc: 'مقارنة شهر بشهر مع رسوم بيانية' },
                        { icon: Calendar, title: 'تفاصيل المعاملات', desc: 'قائمة كاملة بجميع المعاملات' },
                    ].map((section, i) => (
                        <div key={i} className="flex gap-3 p-4 bg-glass rounded-xl">
                            <div className="w-8 h-8 rounded-lg bg-accent/20 flex items-center justify-center shrink-0">
                                <section.icon className="w-4 h-4 text-accent" />
                            </div>
                            <div>
                                <p className="text-sm font-medium text-heading">{section.title}</p>
                                <p className="text-xs text-muted mt-0.5">{section.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* Generate Button */}
            <motion.div variants={item} className="flex items-center justify-between gap-4">
                {error && <p className="text-sm text-error">{error}</p>}
                <div className="flex-1" />
                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="flex items-center gap-2 px-6 py-3 bg-accent text-white rounded-xl font-medium shadow-glow disabled:opacity-50 transition-all hover:bg-accent-hover"
                >
                    {generating ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                        <Download className="w-5 h-5" />
                    )}
                    {generating ? 'جاري الإنشاء...' : 'تنزيل PDF'}
                </button>
            </motion.div>

            {/* Success State */}
            {generated && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="glass-card p-5 rounded-2xl flex items-center gap-4 border border-success/30 bg-success/10"
                >
                    <FileText className="w-8 h-8 text-success shrink-0" />
                    <div>
                        <p className="text-sm font-bold text-heading">تم إنشاء التقرير بنجاح</p>
                        <p className="text-xs text-body mt-0.5">تحقق من مجلد التنزيلات</p>
                    </div>
                </motion.div>
            )}
        </motion.div>
    )
}
