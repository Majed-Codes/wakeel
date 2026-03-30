import { useState, useRef } from 'react'
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle, X, ChevronDown, Building2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { uploadAPI, bankStatementAPI } from '../api'

interface UploadPreview {
    filename: string
    total_rows: number
    columns: string[]
    column_mapping: Record<string, string>
    sample_rows: Record<string, unknown>[]
}

interface UploadResult {
    imported: number
    errors: { row: number; error: string }[]
    filename: string
}

const FIELD_LABELS: Record<string, string> = {
    amount: 'المبلغ',
    date: 'التاريخ',
    vendor: 'الجهة / المورد',
    description: 'الوصف',
    category: 'التصنيف',
}

export default function UploadPage() {
    const [dragging, setDragging] = useState(false)
    const [preview, setPreview] = useState<UploadPreview | null>(null)
    const [result, setResult] = useState<UploadResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [mapping, setMapping] = useState<Record<string, string>>({})
    const fileRef = useRef<HTMLInputElement>(null)

    const handleFile = async (file: File) => {
        if (!file) return
        const ext = file.name.split('.').pop()?.toLowerCase()
        if (!['csv', 'xlsx', 'xls'].includes(ext || '')) {
            setError('يُرجى رفع ملف بصيغة CSV أو Excel فقط')
            return
        }
        setError('')
        setLoading(true)
        setResult(null)
        setPreview(null)
        try {
            const res = await uploadAPI.preview(file)
            setPreview(res.data)
            setMapping(res.data.column_mapping)
        } catch (e: unknown) {
            const err = e as { response?: { data?: { detail?: string } } }
            setError(err.response?.data?.detail || 'فشل في قراءة الملف')
        } finally {
            setLoading(false)
        }
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setDragging(false)
        const file = e.dataTransfer.files[0]
        if (file) handleFile(file)
    }

    const handleConfirm = async () => {
        if (!preview) return
        setLoading(true)
        try {
            const res = await uploadAPI.confirm({
                rows: preview.sample_rows.concat(/* all rows from preview */ []),
                column_mapping: mapping,
            })
            setResult(res.data)
            setPreview(null)
        } catch (e: unknown) {
            const err = e as { response?: { data?: { detail?: string } } }
            setError(err.response?.data?.detail || 'فشل في الاستيراد')
        } finally {
            setLoading(false)
        }
    }

    const reset = () => {
        setPreview(null)
        setResult(null)
        setError('')
        setMapping({})
        if (fileRef.current) fileRef.current.value = ''
    }

    // Bank statement state
    const [bankTab, setBankTab] = useState<'csv' | 'bank'>('csv')
    const [bankFile, setBankFile] = useState<File | null>(null)
    const [bankRows, setBankRows] = useState<Record<string, unknown>[] | null>(null)
    const [bankLoading, setBankLoading] = useState(false)
    const bankInputRef = useRef<HTMLInputElement>(null)

    const handleBankUpload = async (file: File) => {
        setBankFile(file)
        setBankLoading(true)
        try {
            const r = await bankStatementAPI.upload(file)
            setBankRows(r.data.all_rows || [])
        } catch { setBankRows([]) }
        finally { setBankLoading(false) }
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-heading">استيراد المعاملات</h1>
                <p className="text-sm text-body mt-1">ارفع ملف CSV أو كشف حساب بنكي لاستيراد معاملاتك</p>
            </div>

            {/* Tab switcher */}
            <div className="flex gap-1 p-1 bg-glass rounded-xl w-fit border border-glass-border">
                {[{ key: 'csv', label: 'CSV / Excel', icon: FileSpreadsheet },
                  { key: 'bank', label: 'كشف بنكي', icon: Building2 }].map(t => (
                    <button key={t.key} onClick={() => setBankTab(t.key as 'csv' | 'bank')}
                        className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                            bankTab === t.key ? 'bg-accent text-white shadow-glow' : 'text-muted hover:text-heading'
                        }`}>
                        <t.icon size={14} /> {t.label}
                    </button>
                ))}
            </div>

            {/* Bank Statement Tab */}
            {bankTab === 'bank' && (
                <div className="space-y-4">
                    <div
                        className="glass-panel rounded-2xl p-10 text-center cursor-pointer hover:bg-glass-hover transition-colors border-2 border-dashed border-glass-border"
                        onClick={() => bankInputRef.current?.click()}
                    >
                        <Building2 size={40} className="mx-auto text-muted mb-3" />
                        <p className="text-heading font-medium">{bankFile ? bankFile.name : 'ارفع كشف الحساب البنكي'}</p>
                        <p className="text-muted text-sm mt-1">يدعم: الراجحي · SNB · الرياض بنك (PDF أو صورة)</p>
                        <input ref={bankInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
                            onChange={e => e.target.files?.[0] && handleBankUpload(e.target.files[0])} />
                    </div>

                    {bankLoading && <div className="text-center text-muted py-6">جاري تحليل الكشف...</div>}

                    {bankRows && !bankLoading && (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                            className="glass-panel rounded-2xl overflow-hidden">
                            <div className="p-4 border-b border-glass-border flex items-center justify-between">
                                <span className="text-heading font-medium text-sm">تم استخراج {bankRows.length} معاملة</span>
                                <span className="text-xs text-muted">مراجعة الكشف</span>
                            </div>
                            <div className="divide-y divide-glass-border max-h-72 overflow-y-auto">
                                {bankRows.slice(0, 20).map((row, i) => (
                                    <div key={i} className="flex items-center justify-between px-4 py-2.5 text-sm">
                                        <div>
                                            <p className="text-heading text-xs">{String(row.description || '—')}</p>
                                            <p className="text-muted text-xs">{String(row.date || '')}</p>
                                        </div>
                                        <span className={`font-semibold tabular-nums ${row.transaction_type === 'REVENUE' ? 'text-success' : 'text-error'}`}>
                                            {row.transaction_type === 'REVENUE' ? '+' : '-'}{Number(row.amount).toLocaleString('ar-SA')} ر.س
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </div>
            )}

            {/* CSV Tab content is below (existing code) */}
            {bankTab === 'csv' && <div>

            <AnimatePresence mode="wait">
                {/* Result State */}
                {result && (
                    <motion.div
                        key="result"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="glass-card p-8 rounded-2xl text-center space-y-4"
                    >
                        <div className="w-16 h-16 rounded-full bg-success/20 flex items-center justify-center mx-auto">
                            <CheckCircle2 className="w-8 h-8 text-success" />
                        </div>
                        <h2 className="text-xl font-bold text-heading">تم الاستيراد بنجاح</h2>
                        <p className="text-body">
                            تم استيراد <span className="text-success font-bold">{result.imported}</span> معاملة
                            {result.errors.length > 0 && (
                                <span className="text-warning"> • {result.errors.length} أخطاء</span>
                            )}
                        </p>
                        {result.errors.length > 0 && (
                            <div className="bg-warning/10 border border-warning/20 rounded-xl p-4 text-right">
                                <p className="text-xs font-bold text-warning mb-2">الأخطاء:</p>
                                {result.errors.slice(0, 3).map((e, i) => (
                                    <p key={i} className="text-xs text-body">صف {e.row}: {e.error}</p>
                                ))}
                                {result.errors.length > 3 && (
                                    <p className="text-xs text-muted">... و{result.errors.length - 3} أخطاء أخرى</p>
                                )}
                            </div>
                        )}
                        <button onClick={reset} className="px-6 py-2.5 bg-accent text-white rounded-xl font-medium text-sm">
                            رفع ملف آخر
                        </button>
                    </motion.div>
                )}

                {/* Preview State */}
                {preview && !result && (
                    <motion.div
                        key="preview"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                    >
                        {/* File info */}
                        <div className="glass-card p-4 rounded-2xl flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center">
                                    <FileSpreadsheet className="w-5 h-5 text-accent" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-heading">{preview.filename}</p>
                                    <p className="text-xs text-muted">{preview.total_rows} صف</p>
                                </div>
                            </div>
                            <button onClick={reset} className="text-muted hover:text-error transition-colors">
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Column Mapping */}
                        <div className="glass-card p-5 rounded-2xl space-y-3">
                            <h3 className="text-base font-bold text-heading">تعيين الأعمدة</h3>
                            <p className="text-xs text-muted">تحقق من تعيين الأعمدة الصحيحة</p>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {Object.entries(FIELD_LABELS).map(([field, label]) => (
                                    <div key={field} className="space-y-1">
                                        <label className="text-xs text-muted">{label}</label>
                                        <div className="relative">
                                            <select
                                                value={mapping[field] || ''}
                                                onChange={e => setMapping(m => ({ ...m, [field]: e.target.value }))}
                                                className="w-full bg-glass border border-glass-border rounded-xl px-3 py-2 text-sm text-heading appearance-none"
                                            >
                                                <option value="">— غير محدد —</option>
                                                {preview.columns.map(col => (
                                                    <option key={col} value={col}>{col}</option>
                                                ))}
                                            </select>
                                            <ChevronDown className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Sample Data */}
                        <div className="glass-card p-5 rounded-2xl space-y-3">
                            <h3 className="text-base font-bold text-heading">معاينة البيانات ({preview.total_rows} صف)</h3>
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                    <thead>
                                        <tr className="border-b border-glass-border">
                                            {preview.columns.map(col => (
                                                <th key={col} className="px-3 py-2 text-right text-muted font-medium">{col}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {preview.sample_rows.map((row, i) => (
                                            <tr key={i} className="border-b border-glass-border/50 hover:bg-glass-hover">
                                                {preview.columns.map(col => (
                                                    <td key={col} className="px-3 py-2 text-body">
                                                        {String(row[col] ?? '')}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            {preview.total_rows > 5 && (
                                <p className="text-xs text-muted">... و{preview.total_rows - 5} صف آخر</p>
                            )}
                        </div>

                        <div className="flex gap-3 justify-end">
                            <button onClick={reset} className="px-5 py-2.5 text-muted hover:text-white text-sm transition-colors">
                                إلغاء
                            </button>
                            <button
                                onClick={handleConfirm}
                                disabled={loading}
                                className="px-6 py-2.5 bg-accent text-white rounded-xl font-medium text-sm disabled:opacity-50 flex items-center gap-2"
                            >
                                {loading && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                                استيراد {preview.total_rows} معاملة
                            </button>
                        </div>
                    </motion.div>
                )}

                {/* Upload State */}
                {!preview && !result && (
                    <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                        {/* Drop Zone */}
                        <div
                            onDragOver={e => { e.preventDefault(); setDragging(true) }}
                            onDragLeave={() => setDragging(false)}
                            onDrop={handleDrop}
                            onClick={() => fileRef.current?.click()}
                            className={`
                                border-2 border-dashed rounded-2xl p-16 text-center cursor-pointer transition-all
                                ${dragging ? 'border-accent bg-accent/10' : 'border-glass-border hover:border-accent/50 hover:bg-glass-hover'}
                            `}
                        >
                            <input
                                ref={fileRef}
                                type="file"
                                className="hidden"
                                accept=".csv,.xlsx,.xls"
                                onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
                            />
                            <div className="space-y-4">
                                <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mx-auto">
                                    {loading
                                        ? <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                                        : <Upload className="w-8 h-8 text-accent" />
                                    }
                                </div>
                                <div>
                                    <p className="text-lg font-semibold text-heading">اسحب وأفلت الملف هنا</p>
                                    <p className="text-sm text-muted mt-1">أو انقر للاختيار</p>
                                    <p className="text-xs text-muted mt-3">CSV، Excel (.xlsx, .xls) — حتى 10 ميجابايت</p>
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="mt-4 p-4 bg-error/10 border border-error/20 rounded-xl flex items-center gap-3">
                                <AlertCircle className="w-5 h-5 text-error shrink-0" />
                                <p className="text-sm text-error">{error}</p>
                            </div>
                        )}

                        {/* Instructions */}
                        <div className="mt-6 glass-card p-5 rounded-2xl">
                            <h3 className="text-sm font-bold text-heading mb-3">تنسيق الملف المتوقع</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                {Object.entries(FIELD_LABELS).map(([field, label]) => (
                                    <div key={field} className="bg-glass rounded-xl p-3 text-center">
                                        <p className="text-xs text-accent font-medium">{field}</p>
                                        <p className="text-xs text-muted mt-0.5">{label}</p>
                                    </div>
                                ))}
                            </div>
                            <p className="text-xs text-muted mt-3">الأعمدة المطلوبة: المبلغ فقط. الباقي اختياري.</p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
            </div>}
        </div>
    )
}
