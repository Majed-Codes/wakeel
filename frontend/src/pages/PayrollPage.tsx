import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Users, Plus, X, Play, ChevronDown } from 'lucide-react'
import { payrollAPI } from '../api'

interface Employee {
    id: number
    name_ar: string
    name_en: string | null
    job_title: string
    base_salary: number
    is_saudi: boolean
    gosi_enrolled: boolean
    gosi_employer: number
    gosi_employee: number
    net_salary: number
    total_cost: number
    national_id: string | null
}

interface PayrollRun {
    id: number
    month: number
    year: number
    total_gross: number
    total_gosi_employer: number
    total_gosi_employee: number
    total_net: number
    headcount: number
    status: string
    created_at: string
}

const MONTHS_AR = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }
const EMPTY_EMP = { name_ar: '', name_en: '', job_title: '', base_salary: '', is_saudi: true, gosi_enrolled: true, national_id: '', start_date: '' }

export default function PayrollPage() {
    const [tab, setTab] = useState<'employees' | 'runs'>('employees')
    const [employees, setEmployees] = useState<Employee[]>([])
    const [runs, setRuns] = useState<PayrollRun[]>([])
    const [loading, setLoading] = useState(true)
    const [showForm, setShowForm] = useState(false)
    const [form, setForm] = useState({ ...EMPTY_EMP })
    const [saving, setSaving] = useState(false)
    const [runMonth, setRunMonth] = useState(new Date().getMonth() + 1)
    const [runYear, setRunYear] = useState(new Date().getFullYear())
    const [running, setRunning] = useState(false)
    const [runResult, setRunResult] = useState<PayrollRun | null>(null)

    const loadAll = () => {
        setLoading(true)
        Promise.all([
            payrollAPI.employees().catch(() => ({ data: [] })),
            payrollAPI.runs().catch(() => ({ data: [] })),
        ]).then(([empR, runsR]) => {
            setEmployees(empR.data)
            setRuns(runsR.data)
        }).finally(() => setLoading(false))
    }

    useEffect(() => { loadAll() }, [])

    const handleAddEmployee = async () => {
        if (!form.name_ar || !form.base_salary) return
        setSaving(true)
        try {
            await payrollAPI.addEmployee({ ...form, base_salary: Number(form.base_salary) })
            setShowForm(false)
            setForm({ ...EMPTY_EMP })
            loadAll()
        } finally { setSaving(false) }
    }

    const handleRunPayroll = async () => {
        setRunning(true)
        try {
            const r = await payrollAPI.runPayroll(runMonth, runYear)
            setRunResult(r.data)
            loadAll()
        } finally { setRunning(false) }
    }

    const fmt = (n: number) => n.toLocaleString('ar-SA', { maximumFractionDigits: 0 })

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-heading flex items-center gap-3">
                        <Users className="text-accent" size={32} /> الرواتب
                    </h1>
                    <p className="text-body mt-1">إدارة الموظفين وكشوف الرواتب مع حسابات التأمينات</p>
                </div>
                {tab === 'employees' && (
                    <button
                        onClick={() => setShowForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm transition-colors shadow-glow"
                    >
                        <Plus size={16} /> إضافة موظف
                    </button>
                )}
            </div>

            {/* Tabs */}
            <div className="flex gap-1 p-1 bg-glass rounded-xl w-fit border border-glass-border">
                {[{ key: 'employees', label: 'الموظفون' }, { key: 'runs', label: 'كشوف الرواتب' }].map(t => (
                    <button
                        key={t.key}
                        onClick={() => setTab(t.key as 'employees' | 'runs')}
                        className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                            tab === t.key ? 'bg-accent text-white shadow-glow' : 'text-muted hover:text-heading'
                        }`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {loading ? (
                <div className="text-center text-muted py-16">جاري التحميل...</div>
            ) : tab === 'employees' ? (
                /* Employees Tab */
                employees.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-48 text-center">
                        <Users size={48} className="text-muted mb-3" />
                        <p className="text-muted">لا يوجد موظفون بعد</p>
                    </div>
                ) : (
                    <motion.div variants={container} initial="hidden" animate="show" className="space-y-3">
                        {/* Summary bar */}
                        <div className="grid grid-cols-3 gap-4 mb-4">
                            {[
                                { label: 'إجمالي الرواتب', value: employees.reduce((s, e) => s + e.base_salary, 0), color: 'text-heading' },
                                { label: 'تكلفة التأمينات (صاحب)', value: employees.reduce((s, e) => s + e.gosi_employer, 0), color: 'text-warning' },
                                { label: 'التكلفة الإجمالية', value: employees.reduce((s, e) => s + e.total_cost, 0), color: 'text-error' },
                            ].map(s => (
                                <div key={s.label} className="glass-panel rounded-2xl p-4 text-center">
                                    <p className="text-xs text-muted mb-1">{s.label}</p>
                                    <p className={`text-lg font-bold tabular-nums ${s.color}`}>{fmt(s.value)} <span className="text-xs text-muted">ر.س</span></p>
                                </div>
                            ))}
                        </div>

                        {employees.map(e => (
                            <motion.div key={e.id} variants={item} className="glass-panel rounded-2xl p-5">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center text-accent font-bold">
                                            {e.name_ar.charAt(0)}
                                        </div>
                                        <div>
                                            <p className="font-semibold text-heading">{e.name_ar}</p>
                                            <p className="text-xs text-muted">{e.job_title}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-6 text-sm">
                                        <div className="text-center">
                                            <p className="text-xs text-muted">الراتب الأساسي</p>
                                            <p className="font-semibold text-heading tabular-nums">{fmt(e.base_salary)}</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-xs text-muted">تأمين صاحب</p>
                                            <p className="font-semibold text-warning tabular-nums">{fmt(e.gosi_employer)}</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-xs text-muted">تأمين موظف</p>
                                            <p className="font-semibold text-error tabular-nums">{fmt(e.gosi_employee)}</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-xs text-muted">صافي</p>
                                            <p className="font-bold text-success tabular-nums">{fmt(e.net_salary)}</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-3 flex items-center gap-3 text-xs">
                                    <span className={`px-2 py-0.5 rounded-full ${e.is_saudi ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                        {e.is_saudi ? 'سعودي' : 'وافد'}
                                    </span>
                                    {e.gosi_enrolled && <span className="px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">مسجل بالتأمينات</span>}
                                    <span className="text-muted">التكلفة الكاملة: <strong className="text-heading">{fmt(e.total_cost)} ر.س</strong></span>
                                </div>
                            </motion.div>
                        ))}
                    </motion.div>
                )
            ) : (
                /* Payroll Runs Tab */
                <div className="space-y-6">
                    {/* Run Payroll Card */}
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel rounded-2xl p-6">
                        <h3 className="font-semibold text-heading mb-4 flex items-center gap-2">
                            <Play size={18} className="text-accent" /> تشغيل كشف راتب جديد
                        </h3>
                        <div className="flex items-center gap-3">
                            <select value={runMonth} onChange={e => setRunMonth(Number(e.target.value))}
                                className="px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm">
                                {MONTHS_AR.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                            </select>
                            <select value={runYear} onChange={e => setRunYear(Number(e.target.value))}
                                className="px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm">
                                {[2024, 2025, 2026].map(y => <option key={y}>{y}</option>)}
                            </select>
                            <button
                                onClick={handleRunPayroll}
                                disabled={running || employees.length === 0}
                                className="flex items-center gap-2 px-5 py-2 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm transition-colors disabled:opacity-50"
                            >
                                {running ? 'جاري الحساب...' : <><Play size={14} /> تشغيل</>}
                            </button>
                        </div>

                        {/* Last run result */}
                        {runResult && (
                            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                                className="mt-5 pt-5 border-t border-glass-border grid grid-cols-4 gap-4">
                                {[
                                    { label: 'الرواتب الإجمالية', value: runResult.total_gross },
                                    { label: 'تأمين أصحاب', value: runResult.total_gosi_employer },
                                    { label: 'تأمين موظفين', value: runResult.total_gosi_employee },
                                    { label: 'الصافي للصرف', value: runResult.total_net },
                                ].map(s => (
                                    <div key={s.label} className="text-center">
                                        <p className="text-xs text-muted mb-1">{s.label}</p>
                                        <p className="font-bold text-heading tabular-nums">{fmt(s.value)} <span className="text-xs text-muted">ر.س</span></p>
                                    </div>
                                ))}
                            </motion.div>
                        )}
                    </motion.div>

                    {/* Runs History */}
                    {runs.length > 0 && (
                        <div>
                            <h3 className="text-sm font-semibold text-heading mb-3">السجل</h3>
                            <div className="space-y-2">
                                {runs.map(r => (
                                    <div key={r.id} className="glass-panel rounded-xl p-4 flex items-center justify-between">
                                        <div>
                                            <p className="font-medium text-heading text-sm">{MONTHS_AR[r.month - 1]} {r.year}</p>
                                            <p className="text-xs text-muted">{r.headcount} موظف</p>
                                        </div>
                                        <div className="text-left">
                                            <p className="font-bold text-heading tabular-nums text-sm">{fmt(r.total_net)} ر.س صافي</p>
                                            <p className="text-xs text-muted">تكلفة كاملة: {fmt(r.total_gross + r.total_gosi_employer)} ر.س</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Add Employee Modal */}
            {showForm && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                        className="bg-bg-subtle rounded-2xl border border-glass-border p-6 w-full max-w-md shadow-glass">
                        <div className="flex items-center justify-between mb-5">
                            <h2 className="text-lg font-bold text-heading">إضافة موظف</h2>
                            <button onClick={() => setShowForm(false)} className="text-muted hover:text-heading"><X size={20} /></button>
                        </div>

                        <div className="space-y-3">
                            {[
                                { key: 'name_ar', label: 'الاسم بالعربي *' },
                                { key: 'name_en', label: 'الاسم بالإنجليزي' },
                                { key: 'job_title', label: 'المسمى الوظيفي' },
                                { key: 'national_id', label: 'رقم الهوية' },
                                { key: 'base_salary', label: 'الراتب الأساسي (ر.س) *', type: 'number' },
                                { key: 'start_date', label: 'تاريخ الالتحاق', type: 'date' },
                            ].map(f => (
                                <div key={f.key}>
                                    <label className="text-xs text-muted mb-1 block">{f.label}</label>
                                    <input type={f.type || 'text'}
                                        value={(form as Record<string, string | boolean>)[f.key] as string}
                                        onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                                        className="w-full px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm" />
                                </div>
                            ))}

                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 text-sm text-body cursor-pointer">
                                    <input type="checkbox" checked={form.is_saudi}
                                        onChange={e => setForm(p => ({ ...p, is_saudi: e.target.checked }))}
                                        className="w-4 h-4 rounded accent-[#2F80ED]" />
                                    سعودي الجنسية
                                </label>
                                <label className="flex items-center gap-2 text-sm text-body cursor-pointer">
                                    <input type="checkbox" checked={form.gosi_enrolled}
                                        onChange={e => setForm(p => ({ ...p, gosi_enrolled: e.target.checked }))}
                                        className="w-4 h-4 rounded accent-[#2F80ED]" />
                                    مسجل بالتأمينات
                                </label>
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setShowForm(false)} className="flex-1 py-2.5 rounded-xl border border-glass-border text-muted text-sm">إلغاء</button>
                            <button onClick={handleAddEmployee} disabled={saving || !form.name_ar || !form.base_salary}
                                className="flex-1 py-2.5 rounded-xl bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50">
                                {saving ? '...' : 'حفظ'}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    )
}
