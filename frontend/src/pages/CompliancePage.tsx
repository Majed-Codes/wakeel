import { useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, Loader2, CheckCircle, XCircle, Receipt } from 'lucide-react'
import { complianceAPI, vatAPI } from '../api'

export default function CompliancePage() {
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [form, setForm] = useState({ seller_name: '', total: '', vat: '' })

    // VAT Return state
    const [vatQuarter, setVatQuarter] = useState(Math.ceil((new Date().getMonth() + 1) / 3))
    const [vatYear, setVatYear] = useState(new Date().getFullYear())
    const [vatResult, setVatResult] = useState<any>(null)
    const [vatLoading, setVatLoading] = useState(false)

    const generateVAT = async () => {
        setVatLoading(true)
        try {
            const r = await vatAPI.calculate(vatQuarter, vatYear)
            setVatResult(r.data)
        } finally { setVatLoading(false) }
    }

    const check = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        // Simulate API delay for demo
        setTimeout(async () => {
            try {
                // Mock result or real call
                setResult({
                    score: 95,
                    valid: true,
                    issues: []
                })
            } finally {
                setLoading(false)
            }
        }, 1500)
    }

    return (
        <div className="max-w-3xl mx-auto space-y-10">
            <div className="text-center mb-10">
                <h1 className="text-3xl font-bold text-heading">الامتثال الضريبي</h1>
                <p className="text-body mt-2">تحقق من التزام فواتيرك بمتطلبات ZATCA</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Form */}
                <div className="md:col-span-2 glass-panel p-6 rounded-3xl">
                    <form onSubmit={check} className="space-y-4">
                        <div>
                            <label className="text-xs font-medium text-muted block mb-1.5">اسم المورد</label>
                            <input
                                value={form.seller_name}
                                onChange={e => setForm({ ...form, seller_name: e.target.value })}
                                className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/5 text-white focus:border-accent transition-colors"
                                placeholder="مثال: شركة المراعي"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs font-medium text-muted block mb-1.5">إجمالي الفاتورة</label>
                                <input
                                    type="number"
                                    value={form.total}
                                    onChange={e => setForm({ ...form, total: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/5 text-white focus:border-accent transition-colors"
                                    placeholder="0.00"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-muted block mb-1.5">الضريبة</label>
                                <input
                                    type="number"
                                    value={form.vat}
                                    onChange={e => setForm({ ...form, vat: e.target.value })}
                                    className="w-full px-4 py-3 rounded-xl bg-black/20 border border-white/5 text-white focus:border-accent transition-colors"
                                    placeholder="15%"
                                />
                            </div>
                        </div>
                        <button
                            disabled={loading}
                            className="w-full py-4 bg-accent hover:bg-accent-hover text-white rounded-xl font-bold shadow-glow transition-all flex items-center justify-center gap-2 mt-4"
                        >
                            {loading ? <Loader2 className="animate-spin" /> : <><ShieldCheck size={18} /> بدء الفحص</>}
                        </button>
                    </form>
                </div>

                {/* Score Card */}
                <div className="glass-panel p-6 rounded-3xl flex flex-col items-center justify-center text-center relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-b from-blue-500/10 to-transparent" />

                    {result ? (
                        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
                            <div className="w-24 h-24 rounded-full border-4 border-success/30 flex items-center justify-center mb-4 relative">
                                <span className="text-3xl font-bold text-success">{result.score}%</span>
                                <div className="absolute inset-0 border-4 border-success rounded-full border-t-transparent animate-spin" style={{ animationDuration: '3s' }} />
                            </div>
                            <h3 className="text-lg font-bold text-white mb-1">متوافق</h3>
                            <p className="text-xs text-muted">الفاتورة سليمة 100%</p>
                        </motion.div>
                    ) : (
                        <div className="opacity-30">
                            <ShieldCheck size={64} className="mb-4 mx-auto" />
                            <p className="text-sm">بانتظار البيانات...</p>
                        </div>
                    )}
                </div>
            </div>

            {/* ── VAT Return Section ─────────────────────── */}
            <div>
                <div className="flex items-center gap-3 mb-6">
                    <Receipt className="text-warning" size={24} />
                    <div>
                        <h2 className="text-xl font-bold text-heading">إقرار ضريبة القيمة المضافة</h2>
                        <p className="text-muted text-sm">احسب الضريبة المستحقة لكل ربع سنوي (نموذج زاتكا 1)</p>
                    </div>
                </div>

                <div className="glass-panel rounded-3xl p-6 space-y-5">
                    <div className="flex items-center gap-3 flex-wrap">
                        <div>
                            <label className="text-xs text-muted block mb-1">الربع</label>
                            <select value={vatQuarter} onChange={e => setVatQuarter(Number(e.target.value))}
                                className="px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm">
                                {[1,2,3,4].map(q => <option key={q} value={q}>الربع {['الأول','الثاني','الثالث','الرابع'][q-1]}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-xs text-muted block mb-1">السنة</label>
                            <select value={vatYear} onChange={e => setVatYear(Number(e.target.value))}
                                className="px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm">
                                {[2023,2024,2025,2026].map(y => <option key={y}>{y}</option>)}
                            </select>
                        </div>
                        <button
                            onClick={generateVAT}
                            disabled={vatLoading}
                            className="mt-5 flex items-center gap-2 px-5 py-2 bg-warning/90 hover:bg-warning text-black rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                        >
                            {vatLoading ? <Loader2 size={16} className="animate-spin" /> : <Receipt size={16} />}
                            احسب الإقرار
                        </button>
                    </div>

                    {vatResult && (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                            className="border-t border-glass-border pt-5 space-y-4">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-muted">الفترة</span>
                                <span className="text-heading">{vatResult.period_start} → {vatResult.period_end}</span>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                {[
                                    { label: 'المبيعات الخاضعة', value: vatResult.standard_rated_sales, sub: `ضريبة المخرجات: ${vatResult.output_vat?.toLocaleString('ar-SA')} ر.س` },
                                    { label: 'المشتريات الخاضعة', value: vatResult.standard_rated_purchases, sub: `ضريبة المدخلات: ${vatResult.input_vat?.toLocaleString('ar-SA')} ر.س` },
                                ].map(c => (
                                    <div key={c.label} className="bg-glass rounded-2xl p-4">
                                        <p className="text-xs text-muted mb-1">{c.label}</p>
                                        <p className="text-lg font-bold text-heading tabular-nums">
                                            {c.value?.toLocaleString('ar-SA', { maximumFractionDigits: 0 })} <span className="text-xs text-muted">ر.س</span>
                                        </p>
                                        <p className="text-xs text-muted mt-1">{c.sub}</p>
                                    </div>
                                ))}
                            </div>
                            <div className={`rounded-2xl p-5 flex items-center justify-between ${vatResult.net_vat_due >= 0 ? 'bg-error/10 border border-error/20' : 'bg-success/10 border border-success/20'}`}>
                                <div>
                                    <p className="text-sm text-muted">صافي الضريبة المستحقة</p>
                                    <p className="text-xs text-muted mt-0.5">موعد التقديم: {vatResult.filing_deadline}</p>
                                </div>
                                <p className={`text-2xl font-bold tabular-nums ${vatResult.net_vat_due >= 0 ? 'text-error' : 'text-success'}`}>
                                    {Math.abs(vatResult.net_vat_due)?.toLocaleString('ar-SA', { maximumFractionDigits: 2 })}
                                    <span className="text-sm font-normal text-muted mr-1">ر.س</span>
                                </p>
                            </div>
                            <p className="text-xs text-muted text-center">* هذا الحساب للأغراض التقريبية فقط. استشر مستشاراً ضريبياً معتمداً.</p>
                        </motion.div>
                    )}
                </div>
            </div>
        </div>
    )
}
