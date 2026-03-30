import { useState, useEffect } from 'react'
import {
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    Calendar,
    ChevronRight,
    Sparkles,
} from 'lucide-react'
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { forecastAPI, anomaliesAPI, alertsAPI, advisorAPI } from '../api'

const chartData = [
    { name: 'Jan', income: 45000, expenses: 32000 },
    { name: 'Feb', income: 52000, expenses: 28000 },
    { name: 'Mar', income: 48000, expenses: 35000 },
    { name: 'Apr', income: 61000, expenses: 30000 },
    { name: 'May', income: 55000, expenses: 42000 },
    { name: 'Jun', income: 67000, expenses: 38000 },
]

const categoryData = [
    { name: 'تشغيلية', value: 45, color: '#3B82F6' },
    { name: 'رأسمالية', value: 20, color: '#8B5CF6' },
    { name: 'إيرادات', value: 30, color: '#22C55E' },
    { name: 'أخرى', value: 5, color: '#F59E0B' },
]

interface ForecastSummary {
    avg_daily_revenue: number
    avg_daily_expense: number
    predicted_net_30d: number
    trend: string
    risk_level: string
}

interface AnomalyItem {
    title: string
    severity: string
    description: string
}

const item = {
    hidden: { opacity: 0, y: 16 },
    show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
}

const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.07 } },
}

export default function Dashboard() {
    const [forecastSummary, setForecastSummary] = useState<ForecastSummary | null>(null)
    const [anomalies, setAnomalies] = useState<AnomalyItem[]>([])
    const [unreadAlerts, setUnreadAlerts] = useState(0)
    const [advisorScore, setAdvisorScore] = useState<{ health_score: number; action_items: string[] } | null>(null)

    useEffect(() => {
        Promise.all([
            forecastAPI.get(30).catch(() => null),
            anomaliesAPI.list().catch(() => null),
            alertsAPI.count().catch(() => null),
            advisorAPI.get().catch(() => null),
        ]).then(([forecastRes, anomalyRes, alertRes, advisorRes]) => {
            if (forecastRes?.data?.summary) setForecastSummary(forecastRes.data.summary)
            if (anomalyRes?.data) setAnomalies(anomalyRes.data.slice(0, 3))
            if (alertRes?.data) setUnreadAlerts(alertRes.data.unread || 0)
            if (advisorRes?.data) setAdvisorScore({ health_score: advisorRes.data.health_score, action_items: advisorRes.data.action_items || [] })
        })
    }, [])

    const hasExtraCards = forecastSummary !== null || anomalies.length > 0 || unreadAlerts > 0 || advisorScore !== null

    return (
        <div className="space-y-6">

            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <p className="text-xs text-muted uppercase tracking-widest mb-1" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                        Financial Overview
                    </p>
                    <h1 className="text-2xl font-bold text-heading">لوحة التحكم</h1>
                </div>
                <p className="text-xs text-muted" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                    {new Date().toLocaleDateString('ar-SA', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
            </div>

            <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

                {/* Revenue — 2 cols */}
                <motion.div variants={item} className="col-span-1 md:col-span-2 rounded-2xl p-6 border border-white/[0.06] bg-white/[0.02]" style={{ borderTop: '1px solid #22C55E33' }}>
                    <p className="text-xs text-muted mb-3">إجمالي الإيرادات</p>
                    <div className="flex items-end justify-between">
                        <div>
                            <h3 className="text-5xl font-bold text-heading tabular-nums leading-none" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                                142,500
                            </h3>
                            <p className="text-sm text-muted mt-2">ريال سعودي</p>
                        </div>
                        <div className="text-left">
                            <div className="flex items-center gap-1 text-emerald-400 text-sm font-medium">
                                <TrendingUp size={14} />
                                <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>+12.5%</span>
                            </div>
                            <p className="text-xs text-muted mt-1">vs الشهر الماضي</p>
                        </div>
                    </div>
                </motion.div>

                {/* Expenses */}
                <motion.div variants={item} className="rounded-2xl p-6 border border-white/[0.06] bg-white/[0.02]" style={{ borderTop: '1px solid #EF444433' }}>
                    <p className="text-xs text-muted mb-3">المصاريف</p>
                    <h3 className="text-3xl font-bold text-heading tabular-nums leading-none" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                        45,200
                    </h3>
                    <div className="flex items-center gap-1 text-rose-400 text-xs mt-3">
                        <TrendingDown size={12} />
                        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>+5.2%</span>
                        <span className="text-muted">ارتفاع</span>
                    </div>
                </motion.div>

                {/* Net Profit */}
                <motion.div variants={item} className="rounded-2xl p-6 border border-white/[0.06] bg-white/[0.02]" style={{ borderTop: '1px solid #2F80ED33' }}>
                    <p className="text-xs text-muted mb-3">صافي الربح</p>
                    <h3 className="text-3xl font-bold text-heading tabular-nums leading-none" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                        97,300
                    </h3>
                    <div className="flex items-center gap-1 text-emerald-400 text-xs mt-3">
                        <TrendingUp size={12} />
                        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>+18.2%</span>
                        <span className="text-muted">نمو</span>
                    </div>
                </motion.div>

                {/* Chart — 3 cols */}
                <motion.div variants={item} className="col-span-1 md:col-span-2 lg:col-span-3 rounded-2xl p-6 border border-white/[0.06] bg-white/[0.02]">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-sm font-semibold text-heading">التحليل المالي</h3>
                        <div className="flex items-center gap-4 text-xs text-muted">
                            <span className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-[#2F80ED] inline-block" />
                                الإيرادات
                            </span>
                            <span className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-[#8B5CF6] inline-block" />
                                المصاريف
                            </span>
                        </div>
                    </div>
                    <div className="h-[260px] w-full" dir="ltr">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 48, bottom: 4 }}>
                                <defs>
                                    <linearGradient id="gIncome" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#2F80ED" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="#2F80ED" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="gExp" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
                                <XAxis dataKey="name" stroke="transparent" tick={{ fill: '#52525B', fontSize: 11, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} dy={8} />
                                <YAxis stroke="transparent" tick={{ fill: '#52525B', fontSize: 11, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#0d0d0f', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', fontSize: '12px', fontFamily: 'JetBrains Mono' }}
                                    itemStyle={{ color: '#a1a1aa' }}
                                    formatter={(value: number) => [`${value.toLocaleString()} ر.س`]}
                                />
                                <Area type="monotone" dataKey="income" name="الإيرادات" stroke="#2F80ED" strokeWidth={2} fillOpacity={1} fill="url(#gIncome)" />
                                <Area type="monotone" dataKey="expenses" name="المصاريف" stroke="#8B5CF6" strokeWidth={2} fillOpacity={1} fill="url(#gExp)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* Distribution — 1 col */}
                <motion.div variants={item} className="rounded-2xl p-6 border border-white/[0.06] bg-white/[0.02]">
                    <h3 className="text-sm font-semibold text-heading mb-5">التوزيع</h3>
                    <div className="space-y-4">
                        {categoryData.map((cat) => (
                            <div key={cat.name}>
                                <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-xs text-muted">{cat.name}</span>
                                    <span className="text-xs font-medium text-heading tabular-nums" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{cat.value}%</span>
                                </div>
                                <div className="h-1 w-full rounded-full" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }}>
                                    <div
                                        className="h-full rounded-full"
                                        style={{ width: `${cat.value}%`, backgroundColor: cat.color, transition: 'width 0.8s cubic-bezier(0.22,1,0.36,1)' }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* Extra API-driven cards */}
                {hasExtraCards && (
                    <>
                        {forecastSummary && (
                            <motion.div variants={item} className="rounded-2xl p-5 border border-accent/10 bg-white/[0.02]">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2 text-xs text-muted">
                                        <Calendar className="w-3.5 h-3.5 text-accent" />
                                        التنبؤ — 30 يوم
                                    </div>
                                    <Link to="/forecast" className="text-xs text-accent flex items-center gap-0.5 hover:opacity-70 transition-opacity">
                                        عرض <ChevronRight className="w-3 h-3" />
                                    </Link>
                                </div>
                                <div className="space-y-3">
                                    {[
                                        { label: 'إيراد يومي', val: forecastSummary.avg_daily_revenue, color: '#22C55E' },
                                        { label: 'مصروف يومي', val: forecastSummary.avg_daily_expense, color: '#EF4444' },
                                        { label: 'الصافي المتوقع', val: forecastSummary.predicted_net_30d, color: forecastSummary.predicted_net_30d >= 0 ? '#22C55E' : '#EF4444' },
                                    ].map(row => (
                                        <div key={row.label} className="flex justify-between items-center">
                                            <span className="text-xs text-muted">{row.label}</span>
                                            <span className="text-xs font-medium tabular-nums" style={{ color: row.color, fontFamily: "'JetBrains Mono', monospace" }}>
                                                {row.val.toLocaleString('ar-SA')} ر.س
                                            </span>
                                        </div>
                                    ))}
                                </div>
                                <div className="mt-3 pt-3 border-t border-white/[0.05]">
                                    <span className="text-xs text-muted">
                                        {forecastSummary.trend === 'growing' ? 'نمو' : forecastSummary.trend === 'declining' ? 'انخفاض' : 'مستقر'}
                                        {' · '}مخاطر {forecastSummary.risk_level === 'high' ? 'مرتفعة' : forecastSummary.risk_level === 'medium' ? 'متوسطة' : 'منخفضة'}
                                    </span>
                                </div>
                            </motion.div>
                        )}

                        {anomalies.length > 0 && (
                            <motion.div variants={item} className="rounded-2xl p-5 border border-amber-500/10 bg-white/[0.02]">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2 text-xs text-muted">
                                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                                        شذوذات مكتشفة
                                    </div>
                                    <span className="text-xs tabular-nums text-amber-400" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{anomalies.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {anomalies.map((a, i) => (
                                        <p key={i} className="text-xs text-muted leading-relaxed border-r-2 pr-2" style={{ borderColor: a.severity === 'high' ? '#EF4444' : '#F59E0B' }}>
                                            {a.title}
                                        </p>
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        {unreadAlerts > 0 && (
                            <motion.div variants={item} className="col-span-1 md:col-span-2 lg:col-span-4 rounded-xl px-5 py-3.5 border border-accent/10 bg-accent/[0.04] flex items-center justify-between">
                                <p className="text-xs text-muted">
                                    <span className="text-heading font-medium tabular-nums" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{unreadAlerts}</span>
                                    {' '}تنبيه غير مقروء
                                </p>
                                <Link to="/alerts" className="text-xs text-accent hover:opacity-70 transition-opacity cursor-pointer">
                                    عرض التنبيهات
                                </Link>
                            </motion.div>
                        )}

                        {advisorScore && (
                            <motion.div variants={item} className="rounded-2xl p-5 border border-white/[0.06] bg-white/[0.02]">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2 text-xs text-muted">
                                        <Sparkles className="w-3.5 h-3.5 text-accent" />
                                        الصحة المالية
                                    </div>
                                    <Link to="/advisor" className="text-xs text-accent flex items-center gap-0.5 hover:opacity-70 transition-opacity">
                                        عرض <ChevronRight className="w-3 h-3" />
                                    </Link>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className="text-4xl font-bold tabular-nums leading-none" style={{
                                        fontFamily: "'JetBrains Mono', monospace",
                                        color: advisorScore.health_score >= 70 ? '#22C55E' : advisorScore.health_score >= 40 ? '#F59E0B' : '#EF4444'
                                    }}>
                                        {advisorScore.health_score}
                                        <span className="text-sm font-normal text-muted">/100</span>
                                    </span>
                                    <div className="flex-1 space-y-1.5">
                                        {advisorScore.action_items.slice(0, 2).map((a, i) => (
                                            <p key={i} className="text-xs text-muted truncate leading-relaxed">— {a}</p>
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </>
                )}
            </motion.div>
        </div>
    )
}
