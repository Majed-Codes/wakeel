import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Building2, Plus, Search, X, Phone, Mail, Clock, Trash2 } from 'lucide-react'
import { vendorsAPI } from '../api'

interface Vendor {
    id: number
    name: string
    category: string | null
    contact_phone: string | null
    contact_email: string | null
    payment_terms_days: number
    notes: string | null
    total_spent: number
    transaction_count: number
    created_at: string
}

interface Transaction {
    id: number
    amount: number
    description: string
    date: string
    category: string
    transaction_type: string
}

const CATEGORY_COLORS: Record<string, string> = {
    'تشغيلية': 'bg-blue-500/20 text-blue-400',
    'رأسمالية': 'bg-purple-500/20 text-purple-400',
    'إيرادات': 'bg-emerald-500/20 text-emerald-400',
    'رواتب': 'bg-amber-500/20 text-amber-400',
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

const EMPTY_FORM = { name: '', category: '', contact_phone: '', contact_email: '', payment_terms_days: 30, notes: '' }

export default function VendorsPage() {
    const [vendors, setVendors] = useState<Vendor[]>([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [showForm, setShowForm] = useState(false)
    const [form, setForm] = useState({ ...EMPTY_FORM })
    const [saving, setSaving] = useState(false)
    const [selected, setSelected] = useState<Vendor | null>(null)
    const [selectedTxs, setSelectedTxs] = useState<Transaction[]>([])

    const load = () => {
        setLoading(true)
        vendorsAPI.list()
            .then(r => setVendors(r.data))
            .catch(() => setVendors([]))
            .finally(() => setLoading(false))
    }

    useEffect(() => { load() }, [])

    const handleCreate = async () => {
        if (!form.name.trim()) return
        setSaving(true)
        try {
            await vendorsAPI.create({ ...form, payment_terms_days: Number(form.payment_terms_days) })
            setShowForm(false)
            setForm({ ...EMPTY_FORM })
            load()
        } finally { setSaving(false) }
    }

    const handleDelete = async (id: number) => {
        await vendorsAPI.delete(id)
        if (selected?.id === id) setSelected(null)
        load()
    }

    const openVendor = async (v: Vendor) => {
        setSelected(v)
        try {
            const r = await vendorsAPI.transactions(v.id)
            setSelectedTxs(r.data)
        } catch { setSelectedTxs([]) }
    }

    const filtered = vendors.filter(v =>
        v.name.toLowerCase().includes(search.toLowerCase()) ||
        (v.category || '').toLowerCase().includes(search.toLowerCase())
    )

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-heading flex items-center gap-3">
                        <Building2 className="text-accent" size={32} /> الموردون
                    </h1>
                    <p className="text-body mt-1">إدارة الموردين والمتعاملين</p>
                </div>
                <button
                    onClick={() => setShowForm(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm transition-colors shadow-glow"
                >
                    <Plus size={16} /> إضافة مورد
                </button>
            </div>

            {/* Search */}
            <div className="relative">
                <Search size={18} className="absolute top-1/2 -translate-y-1/2 right-4 text-muted" />
                <input
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="بحث عن مورد..."
                    className="w-full pr-12 pl-4 py-3 rounded-xl border border-glass-border text-heading bg-glass placeholder:text-muted"
                />
            </div>

            {/* Vendor Grid */}
            {loading ? (
                <div className="text-center text-muted py-16">جاري التحميل...</div>
            ) : filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center">
                    <Building2 size={48} className="text-muted mb-3" />
                    <p className="text-muted">{search ? 'لا توجد نتائج' : 'لا يوجد موردون بعد'}</p>
                </div>
            ) : (
                <motion.div
                    variants={container}
                    initial="hidden"
                    animate="show"
                    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
                >
                    {filtered.map(v => (
                        <motion.div
                            key={v.id}
                            variants={item}
                            onClick={() => openVendor(v)}
                            className="glass-panel rounded-2xl p-5 cursor-pointer hover:bg-glass-hover transition-colors"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <h3 className="font-semibold text-heading">{v.name}</h3>
                                    {v.category && (
                                        <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[v.category] || 'bg-glass text-muted'}`}>
                                            {v.category}
                                        </span>
                                    )}
                                </div>
                                <button
                                    onClick={e => { e.stopPropagation(); handleDelete(v.id) }}
                                    className="text-muted hover:text-error transition-colors"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>

                            <div className="space-y-1.5 text-sm text-muted">
                                {v.contact_phone && (
                                    <div className="flex items-center gap-2">
                                        <Phone size={13} /> {v.contact_phone}
                                    </div>
                                )}
                                {v.contact_email && (
                                    <div className="flex items-center gap-2">
                                        <Mail size={13} /> {v.contact_email}
                                    </div>
                                )}
                                <div className="flex items-center gap-2">
                                    <Clock size={13} /> شروط الدفع: {v.payment_terms_days} يوم
                                </div>
                            </div>

                            <div className="mt-4 pt-3 border-t border-glass-border flex justify-between text-xs">
                                <span className="text-muted">{v.transaction_count} معاملة</span>
                                <span className="text-heading font-semibold tabular-nums">
                                    {v.total_spent.toLocaleString('ar-SA', { maximumFractionDigits: 0 })} ر.س
                                </span>
                            </div>
                        </motion.div>
                    ))}
                </motion.div>
            )}

            {/* Vendor Detail Slide-over */}
            <AnimatePresence>
                {selected && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setSelected(null)}
                            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
                        />
                        <motion.div
                            initial={{ x: '100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                            className="fixed inset-y-0 left-0 z-50 w-full max-w-md bg-bg-subtle border-r border-glass-border shadow-glass flex flex-col"
                        >
                            <div className="flex items-center justify-between p-6 border-b border-glass-border">
                                <div>
                                    <h2 className="text-lg font-bold text-heading">{selected.name}</h2>
                                    <p className="text-muted text-sm">{selected.category || 'بدون فئة'}</p>
                                </div>
                                <button onClick={() => setSelected(null)} className="text-muted hover:text-heading">
                                    <X size={20} />
                                </button>
                            </div>

                            <div className="p-6 space-y-3 text-sm border-b border-glass-border">
                                {selected.contact_phone && <p><span className="text-muted">الهاتف:</span> <span className="text-heading">{selected.contact_phone}</span></p>}
                                {selected.contact_email && <p><span className="text-muted">البريد:</span> <span className="text-heading">{selected.contact_email}</span></p>}
                                <p><span className="text-muted">شروط الدفع:</span> <span className="text-heading">{selected.payment_terms_days} يوم</span></p>
                                <p><span className="text-muted">إجمالي الإنفاق:</span> <span className="text-heading font-semibold">{selected.total_spent.toLocaleString('ar-SA')} ر.س</span></p>
                                {selected.notes && <p className="text-body">{selected.notes}</p>}
                            </div>

                            <div className="flex-1 overflow-y-auto p-6">
                                <h3 className="text-sm font-semibold text-heading mb-3">آخر المعاملات</h3>
                                {selectedTxs.length === 0 ? (
                                    <p className="text-muted text-sm">لا توجد معاملات</p>
                                ) : (
                                    <div className="space-y-2">
                                        {selectedTxs.map(tx => (
                                            <div key={tx.id} className="glass-panel rounded-xl p-3 flex items-center justify-between">
                                                <div>
                                                    <p className="text-xs text-heading">{tx.description || '—'}</p>
                                                    <p className="text-xs text-muted">{tx.date?.slice(0, 10)}</p>
                                                </div>
                                                <span className={`text-sm font-semibold tabular-nums ${tx.transaction_type === 'REVENUE' ? 'text-success' : 'text-error'}`}>
                                                    {tx.transaction_type === 'REVENUE' ? '+' : '-'}{tx.amount.toLocaleString('ar-SA')} ر.س
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* Add Vendor Modal */}
            {showForm && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-bg-subtle rounded-2xl border border-glass-border p-6 w-full max-w-md shadow-glass"
                    >
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-lg font-bold text-heading">إضافة مورد جديد</h2>
                            <button onClick={() => setShowForm(false)} className="text-muted hover:text-heading">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { key: 'name', label: 'اسم المورد *', span: 2 },
                                { key: 'category', label: 'الفئة' },
                                { key: 'payment_terms_days', label: 'شروط الدفع (يوم)', type: 'number' },
                                { key: 'contact_phone', label: 'رقم الهاتف' },
                                { key: 'contact_email', label: 'البريد الإلكتروني' },
                            ].map(f => (
                                <div key={f.key} className={f.span === 2 ? 'col-span-2' : ''}>
                                    <label className="text-xs text-muted mb-1 block">{f.label}</label>
                                    <input
                                        type={f.type || 'text'}
                                        value={(form as Record<string, string | number>)[f.key] as string}
                                        onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                                        className="w-full px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm"
                                    />
                                </div>
                            ))}
                            <div className="col-span-2">
                                <label className="text-xs text-muted mb-1 block">ملاحظات</label>
                                <textarea
                                    rows={2}
                                    value={form.notes}
                                    onChange={e => setForm(p => ({ ...p, notes: e.target.value }))}
                                    className="w-full px-3 py-2 rounded-xl border border-glass-border text-heading bg-glass text-sm resize-none"
                                />
                            </div>
                        </div>

                        <div className="flex gap-3 mt-6">
                            <button onClick={() => setShowForm(false)} className="flex-1 py-2.5 rounded-xl border border-glass-border text-muted text-sm">إلغاء</button>
                            <button
                                onClick={handleCreate}
                                disabled={saving || !form.name.trim()}
                                className="flex-1 py-2.5 rounded-xl bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50"
                            >
                                {saving ? '...' : 'حفظ'}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    )
}
