import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { PiggyBank, Plus, Trash2, X, TrendingUp } from 'lucide-react'
import { budgetAPI } from '../api'

const CATEGORIES = ['تشغيلية', 'رأسمالية', 'إيرادات', 'رواتب', 'تسويق', 'إيجار', 'مرافق', 'أخرى']
const COLORS: Record<string, string> = {
    'تشغيلية': '#3B82F6', 'رأسمالية': '#8B5CF6', 'إيرادات': '#10B981',
    'رواتب': '#F59E0B', 'تسويق': '#EC4899', 'إيجار': '#6366F1',
    'مرافق': '#14B8A6', 'أخرى': '#A1A1AA',
}

interface Budget {
    id: number
    category: string
    amount: number
    month: number
    year: number
    spent: number
    remaining: number
    pct_used: number
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const MONTHS_AR = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']

export default function BudgetPage() {
    const now = new Date()
    const [month, setMonth] = useState(now.getMonth() + 1)
    const [year, setYear] = useState(now.getFullYear())
    const [budgets, setBudgets] = useState<Budget[]>([])
    const [loading, setLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [form, setForm] = useState({ category: CATEGORIES[0], amount: '' })
    const [saving, setSaving] = useState(false)

    const fetchBudgets = () => {
        setLoading(true)
        budgetAPI.list(month, year)
            .then(r => setBudgets(r.data))
            .catch(() => setBudgets([]))
            .finally(() => setLoading(false))
    }

    useEffect(() => { fetchBudgets() }, [month, year])

    const handleCreate = async () => {
        if (!form.amount || Number(form.amount) <= 0) return
        setSaving(true)
        try {
            await budgetAPI.create({ category: form.category, amount: Number(form.amount), month, year })
            setShowModal(false)
            setForm({ category: CATEGORIES[0], amount: '' })
            fetchBudgets()
        } finally { setSaving(false) }
    }

    const handleDelete = async (id: number) => {
        await budgetAPI.delete(id)
        fetchBudgets()
    }

    const barColor = (pct: number) => pct >= 100 ? '#FF3B30' : pct >= 75 ? '#FFCC00' : '#34C759'

    const totalBudget = budgets.reduce((s, b) => s + b.amount, 0)
    const totalSpent = budgets.reduce((s, b) => s + b.spent, 0)

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-heading flex items-center gap-3">
                        <PiggyBank className="text-accent" size={32} /> الميزانية
                    </h1>
                    <p className="text-body mt-1">تتبع الميزانية الشهرية لكل فئة</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm transition-colors shadow-glow"
                >
                    <Plus size={16} /> إضافة ميزانية
                </button>
            </div>

            {/* Month/Year Selector */}
            <div className="flex items-center gap-3">
                <select
                    value={month}
                    onChange={e => setMonth(Number(e.target.value))}
                    className="px-3 py-2 rounded-xl border border-glass-border text-heading text-sm bg-glass"
                >
                    {MONTHS_AR.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                </select>
                <select
                    value={year}
                    onChange={e => setYear(Number(e.target.value))}
                    className="px-3 py-2 rounded-xl border border-glass-border text-heading text-sm bg-glass"
                >
                    {[2024, 2025, 2026].map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <span className="text-muted text-sm">{MONTHS_AR[month - 1]} {year}</span>
            </div>

            {/* Summary */}
            {budgets.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="grid grid-cols-3 gap-4"
                >
                    {[
                        { label: 'إجمالي الميزانية', value: totalBudget, color: 'text-heading' },
                        { label: 'إجمالي الإنفاق', value: totalSpent, color: 'text-warning' },
                        { label: 'المتبقي', value: totalBudget - totalSpent, color: totalBudget - totalSpent >= 0 ? 'text-success' : 'text-error' },
                    ].map(s => (
                        <div key={s.label} className="glass-panel rounded-2xl p-4 text-center">
                            <p className="text-xs text-muted mb-1">{s.label}</p>
                            <p className={`text-xl font-bold ${s.color} tabular-nums`}>
                                {s.value.toLocaleString('ar-SA', { maximumFractionDigits: 0 })} <span className="text-sm font-normal text-muted">ر.س</span>
                            </p>
                        </div>
                    ))}
                </motion.div>
            )}

            {/* Budget Cards */}
            {loading ? (
                <div className="flex items-center justify-center h-48 text-muted">جاري التحميل...</div>
            ) : budgets.length === 0 ? (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex flex-col items-center justify-center h-48 text-center"
                >
                    <PiggyBank size={48} className="text-muted mb-3" />
                    <p className="text-muted">لا توجد ميزانية لهذا الشهر</p>
                    <p className="text-muted text-sm mt-1">أضف ميزانية لكل فئة لتتبع الإنفاق</p>
                </motion.div>
            ) : (
                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="grid grid-cols-1 md:grid-cols-2 gap-4"
                >
                    {budgets.map(b => (
                        <motion.div key={b.id} variants={item} className="glass-panel rounded-2xl p-5">
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full" style={{ background: COLORS[b.category] || '#A1A1AA' }} />
                                    <span className="font-semibold text-heading">{b.category}</span>
                                </div>
                                <button
                                    onClick={() => handleDelete(b.id)}
                                    className="text-muted hover:text-error transition-colors"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>

                            {/* Amounts */}
                            <div className="flex justify-between text-sm mb-3">
                                <span className="text-muted">
                                    أُنفق: <span className="text-heading font-medium tabular-nums">
                                        {b.spent.toLocaleString('ar-SA', { maximumFractionDigits: 0 })}
                                    </span> ر.س
                                </span>
                                <span className="text-muted">
                                    من: <span className="text-heading font-medium tabular-nums">
                                        {b.amount.toLocaleString('ar-SA', { maximumFractionDigits: 0 })}
                                    </span> ر.س
                                </span>
                            </div>

                            {/* Progress bar */}
                            <div className="h-2.5 w-full bg-glass-border rounded-full overflow-hidden">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${Math.min(b.pct_used, 100)}%` }}
                                    transition={{ duration: 0.7, ease: 'easeOut' }}
                                    className="h-full rounded-full"
                                    style={{ background: barColor(b.pct_used) }}
                                />
                            </div>

                            <div className="flex justify-between items-center mt-2 text-xs">
                                <span style={{ color: barColor(b.pct_used) }} className="font-semibold">
                                    {b.pct_used.toFixed(1)}%
                                </span>
                                <span className={b.remaining >= 0 ? 'text-success' : 'text-error'}>
                                    {b.remaining >= 0 ? `متبقي ${b.remaining.toLocaleString('ar-SA', { maximumFractionDigits: 0 })} ر.س` : 'تجاوز الميزانية'}
                                </span>
                            </div>
                        </motion.div>
                    ))}
                </motion.div>
            )}

            {/* Add Budget Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-bg-subtle rounded-2xl border border-glass-border p-6 w-full max-w-sm shadow-glass"
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-heading">إضافة ميزانية</h2>
                            <button onClick={() => setShowModal(false)} className="text-muted hover:text-heading">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="text-sm text-muted mb-1 block">الفئة</label>
                                <select
                                    value={form.category}
                                    onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                                    className="w-full px-3 py-2.5 rounded-xl border border-glass-border text-heading bg-glass"
                                >
                                    {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="text-sm text-muted mb-1 block">المبلغ (ر.س)</label>
                                <input
                                    type="number"
                                    min="1"
                                    placeholder="مثال: 5000"
                                    value={form.amount}
                                    onChange={e => setForm(f => ({ ...f, amount: e.target.value }))}
                                    className="w-full px-3 py-2.5 rounded-xl border border-glass-border text-heading bg-glass"
                                />
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 py-2.5 rounded-xl border border-glass-border text-muted hover:text-heading transition-colors text-sm"
                            >
                                إلغاء
                            </button>
                            <button
                                onClick={handleCreate}
                                disabled={saving || !form.amount}
                                className="flex-1 py-2.5 rounded-xl bg-accent hover:bg-accent-hover text-white transition-colors text-sm disabled:opacity-50 flex items-center justify-center gap-2"
                            >
                                {saving ? '...' : <><Plus size={14} /> حفظ</>}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    )
}
