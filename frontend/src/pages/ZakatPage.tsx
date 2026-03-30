import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Star, RefreshCw, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react'
import { zakatAPI } from '../api'

interface ZakatResult {
    zakatable_assets: number
    liabilities: number
    net_assets: number
    nisab_threshold: number
    zakat_due: number
    is_above_nisab: boolean
    hawl_reminder: string
    calculation_date: string
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

export default function ZakatPage() {
    const [result, setResult] = useState<ZakatResult | null>(null)
    const [loading, setLoading] = useState(true)
    const [showExplainer, setShowExplainer] = useState(false)

    const load = () => {
        setLoading(true)
        zakatAPI.calculate()
            .then(r => setResult(r.data))
            .catch(() => setResult(null))
            .finally(() => setLoading(false))
    }

    useEffect(() => { load() }, [])

    const fmt = (n: number) => n.toLocaleString('ar-SA', { maximumFractionDigits: 2 })

    const cards = result ? [
        { label: 'إجمالي الأصول', value: result.zakatable_assets, icon: '💰', color: 'text-success' },
        { label: 'الالتزامات', value: result.liabilities, icon: '📊', color: 'text-error' },
        { label: 'صافي الأصول', value: result.net_assets, icon: '⚖️', color: result.net_assets >= 0 ? 'text-heading' : 'text-error' },
        { label: 'حد النصاب', value: result.nisab_threshold, icon: '🏛️', color: 'text-warning' },
    ] : []

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-heading flex items-center gap-3">
                        <Star className="text-warning" size={32} fill="currentColor" /> حاسبة الزكاة
                    </h1>
                    <p className="text-body mt-1">احتساب زكاة المال وفق أحكام الشريعة الإسلامية</p>
                </div>
                <button
                    onClick={load}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-glass border border-glass-border rounded-xl text-sm text-heading hover:bg-glass-hover transition-colors"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> إعادة الحساب
                </button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-64 text-muted">
                    <RefreshCw size={24} className="animate-spin ml-2" /> جاري الحساب...
                </div>
            ) : !result ? (
                <div className="flex flex-col items-center justify-center h-64 text-center">
                    <AlertCircle size={48} className="text-muted mb-3" />
                    <p className="text-muted">تعذّر حساب الزكاة. تأكد من وجود معاملات مسجّلة.</p>
                </div>
            ) : (
                <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
                    {/* Four metric cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {cards.map(c => (
                            <motion.div key={c.label} variants={item} className="glass-panel rounded-2xl p-4 text-center">
                                <div className="text-2xl mb-2">{c.icon}</div>
                                <p className="text-xs text-muted mb-1">{c.label}</p>
                                <p className={`text-lg font-bold tabular-nums ${c.color}`}>
                                    {fmt(c.value)}
                                    <span className="text-xs font-normal text-muted mr-1">ر.س</span>
                                </p>
                            </motion.div>
                        ))}
                    </div>

                    {/* Zakat Due — hero card */}
                    <motion.div
                        variants={item}
                        className={`rounded-3xl p-8 text-center border-2 ${
                            result.is_above_nisab
                                ? 'bg-warning/10 border-warning/30'
                                : 'glass-panel border-success/30'
                        }`}
                    >
                        <p className="text-sm text-muted mb-2">الزكاة المستحقة</p>
                        {result.is_above_nisab ? (
                            <>
                                <p className="text-5xl font-bold text-warning tabular-nums mb-2">
                                    {fmt(result.zakat_due)}
                                </p>
                                <p className="text-warning text-lg">ريال سعودي</p>
                                <p className="text-xs text-muted mt-3">
                                    {(result.net_assets * 100 / result.nisab_threshold).toFixed(1)}% من النصاب × 2.5% = {fmt(result.zakat_due)} ر.س
                                </p>
                            </>
                        ) : (
                            <>
                                <p className="text-5xl font-bold text-success mb-2">لا زكاة</p>
                                <p className="text-muted text-sm mt-2">
                                    صافي أصولك ({fmt(result.net_assets)} ر.س) أقل من حد النصاب ({fmt(result.nisab_threshold)} ر.س)
                                </p>
                            </>
                        )}
                    </motion.div>

                    {/* Hawl reminder */}
                    <motion.div variants={item} className="glass-panel rounded-2xl p-4 flex gap-3">
                        <AlertCircle size={20} className="text-warning flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-body">{result.hawl_reminder}</p>
                    </motion.div>

                    {/* Explainer accordion */}
                    <motion.div variants={item} className="glass-panel rounded-2xl overflow-hidden">
                        <button
                            onClick={() => setShowExplainer(!showExplainer)}
                            className="w-full flex items-center justify-between p-5 text-heading font-medium hover:bg-glass-hover transition-colors"
                        >
                            <span>كيف تُحسب الزكاة؟</span>
                            {showExplainer ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {showExplainer && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                className="px-5 pb-5 space-y-3 text-sm text-body border-t border-glass-border"
                            >
                                <p className="pt-4"><strong className="text-heading">١. حساب الأصول:</strong> مجموع الإيرادات خلال السنة الهجرية الماضية.</p>
                                <p><strong className="text-heading">٢. طرح الالتزامات:</strong> مجموع المصاريف والديون المستحقة.</p>
                                <p><strong className="text-heading">٣. مقارنة بالنصاب:</strong> حد النصاب = 85 جرام ذهب ≈ {fmt(result.nisab_threshold)} ر.س (2025م).</p>
                                <p><strong className="text-heading">٤. حساب الزكاة:</strong> إذا بلغ صافي الأصول النصاب، تُخرج 2.5% منه.</p>
                                <p className="text-xs text-muted mt-2">* استشر عالماً شرعياً للحالات المعقدة.</p>
                            </motion.div>
                        )}
                    </motion.div>

                    <p className="text-xs text-muted text-center">تاريخ الحساب: {result.calculation_date}</p>
                </motion.div>
            )}
        </div>
    )
}
