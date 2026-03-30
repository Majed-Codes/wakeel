import { useState, useEffect } from 'react'
import {
    TrendingUp,
    TrendingDown,
    Activity,
    ArrowUpRight,
    CreditCard,
    DollarSign,
    MoreHorizontal,
    AlertTriangle,
    Calendar,
    ChevronRight,
    Sparkles
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
import { dashboardAPI, forecastAPI, anomaliesAPI, alertsAPI, advisorAPI } from '../api'

// Mock Data incase API fails
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
    { name: 'إيرادات', value: 30, color: '#10B981' },
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

export default function Dashboard() {
    const [loading, setLoading] = useState(true)
    const [forecastSummary, setForecastSummary] = useState<ForecastSummary | null>(null)
    const [anomalies, setAnomalies] = useState<AnomalyItem[]>([])
    const [unreadAlerts, setUnreadAlerts] = useState(0)
    const [advisorScore, setAdvisorScore] = useState<{ health_score: number; action_items: string[] } | null>(null)

    useEffect(() => {
        // Load dashboard data
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
        }).finally(() => {
            setTimeout(() => setLoading(false), 400)
        })
    }, [])

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1
            }
        }
    }

    const item = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0 }
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-heading">لوحة التحكم</h1>
                    <p className="text-body mt-1">نظرة عامة على أدائك المالي</p>
                </div>
                <div className="flex gap-2">
                    <button className="px-4 py-2 bg-glass border border-glass-border rounded-xl text-sm hover:bg-glass-hover transition-colors">تصدير</button>
                    <button className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-xl text-sm transition-colors shadow-glow">تقرير جديد</button>
                </div>
            </div>

            {/* Bento Grid */}
            <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
            >
                {/* Stat 1: Revenue (Large - 2 cols) */}
                <motion.div variants={item} className="col-span-1 md:col-span-2 glass-panel rounded-3xl p-6 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-accent/20 blur-[50px] rounded-full group-hover:bg-accent/30 transition-colors" />
                    <div className="relative z-10 flex justify-between items-start">
                        <div>
                            <p className="text-sm text-muted font-medium mb-1">إجمالي الإيرادات</p>
                            <h3 className="text-4xl font-bold text-heading tabular-nums">142,500 <span className="text-lg text-muted font-normal">ر.س</span></h3>
                            <div className="flex items-center gap-2 mt-4 text-emerald-400 text-sm font-medium bg-emerald-400/10 px-2 py-1 rounded-lg w-fit">
                                <TrendingUp size={16} />
                                <span>+12.5%</span>
                                <span className="text-muted font-normal text-xs">مقارنة بالشهر الماضي</span>
                            </div>
                        </div>
                        <div className="w-12 h-12 rounded-full bg-glass flex items-center justify-center border border-glass-border">
                            <DollarSign className="text-accent" />
                        </div>
                    </div>
                </motion.div>

                {/* Stat 2: Expenses */}
                <motion.div variants={item} className="glass-panel rounded-3xl p-6 relative overflow-hidden">
                    <div className="absolute bottom-0 left-0 w-24 h-24 bg-purple-500/20 blur-[40px] rounded-full" />
                    <div className="flex justify-between items-start mb-4">
                        <div className="w-10 h-10 rounded-full bg-glass flex items-center justify-center border border-glass-border">
                            <Activity className="text-purple-400" size={20} />
                        </div>
                        <MoreHorizontal className="text-muted cursor-pointer hover:text-white" size={20} />
                    </div>
                    <p className="text-sm text-muted font-medium">المصاريف</p>
                    <h3 className="text-2xl font-bold text-heading mt-1 tabular-nums">45,200</h3>
                    <p className="text-xs text-rose-400 mt-2 flex items-center gap-1">
                        <TrendingDown size={12} />
                        +5.2% ارتفاع
                    </p>
                </motion.div>

                {/* Stat 3: Net Profit */}
                <motion.div variants={item} className="glass-panel rounded-3xl p-6 relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-24 h-24 bg-emerald-500/20 blur-[40px] rounded-full" />
                    <div className="flex justify-between items-start mb-4">
                        <div className="w-10 h-10 rounded-full bg-glass flex items-center justify-center border border-glass-border">
                            <CreditCard className="text-emerald-400" size={20} />
                        </div>
                        <MoreHorizontal className="text-muted cursor-pointer hover:text-white" size={20} />
                    </div>
                    <p className="text-sm text-muted font-medium">صافي الربح</p>
                    <h3 className="text-2xl font-bold text-heading mt-1 tabular-nums">97,300</h3>
                    <p className="text-xs text-emerald-400 mt-2 flex items-center gap-1">
                        <ArrowUpRight size={12} />
                        +18.2% نمو
                    </p>
                </motion.div>

                {/* Main Curve Chart (3 cols) */}
                <motion.div variants={item} className="col-span-1 md:col-span-2 lg:col-span-3 glass-panel rounded-3xl p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-lg font-bold text-heading">التحليل المالي</h3>
                        <div className="flex items-center gap-4 text-xs text-muted">
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#2F80ED] inline-block" />الإيرادات</span>
                            <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-[#8B5CF6] inline-block" />المصاريف</span>
                        </div>
                    </div>
                    <div className="h-[280px] w-full" dir="ltr">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 55, bottom: 5 }}>
                                <defs>
                                    <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#2F80ED" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#2F80ED" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="colorExp" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis dataKey="name" stroke="#52525B" tick={{ fill: '#71717A', fontSize: 12 }} axisLine={false} tickLine={false} dy={10} />
                                <YAxis stroke="#52525B" tick={{ fill: '#71717A', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: 'rgba(0,0,0,0.85)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', backdropFilter: 'blur(12px)' }}
                                    itemStyle={{ color: '#fff' }}
                                    formatter={(value: number) => [`${value.toLocaleString()} ر.س`]}
                                />
                                <Area type="monotone" dataKey="income" name="الإيرادات" stroke="#2F80ED" strokeWidth={3} fillOpacity={1} fill="url(#colorIncome)" />
                                <Area type="monotone" dataKey="expenses" name="المصاريف" stroke="#8B5CF6" strokeWidth={3} fillOpacity={1} fill="url(#colorExp)" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </motion.div>

                {/* Distribution (1 col) — same row as chart, sits on the left */}
                <motion.div variants={item} className="glass-panel rounded-3xl p-6">
                    <h3 className="text-lg font-bold text-heading mb-6">التوزيع</h3>
                    <div className="space-y-5">
                        {categoryData.map((cat) => (
                            <div key={cat.name} className="space-y-2">
                                <div className="flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: cat.color }} />
                                        <span className="text-muted font-medium">{cat.name}</span>
                                    </div>
                                    <span className="text-heading font-semibold tabular-nums">{cat.value}%</span>
                                </div>
                                <div className="h-2 w-full bg-glass rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full"
                                        style={{ width: `${cat.value}%`, background: cat.color, transition: 'width 0.7s ease' }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* Forecast Mini-Card */}
                {forecastSummary && (
                    <motion.div variants={item} className="glass-panel rounded-3xl p-6 border border-accent/20">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-bold text-heading flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-accent" />
                                التنبؤ - 30 يوم
                            </h3>
                            <Link to="/forecast" className="text-xs text-accent flex items-center gap-1 hover:underline">
                                التفاصيل <ChevronRight className="w-3 h-3" />
                            </Link>
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs">
                                <span className="text-muted">متوسط إيراد يومي</span>
                                <span className="text-success font-medium">{forecastSummary.avg_daily_revenue.toLocaleString('ar-SA')} ر.س</span>
                            </div>
                            <div className="flex justify-between text-xs">
                                <span className="text-muted">متوسط مصروف يومي</span>
                                <span className="text-error font-medium">{forecastSummary.avg_daily_expense.toLocaleString('ar-SA')} ر.س</span>
                            </div>
                            <div className="flex justify-between text-xs border-t border-glass-border pt-2 mt-2">
                                <span className="text-muted">الصافي المتوقع</span>
                                <span className={`font-bold ${forecastSummary.predicted_net_30d >= 0 ? 'text-success' : 'text-error'}`}>
                                    {forecastSummary.predicted_net_30d.toLocaleString('ar-SA')} ر.س
                                </span>
                            </div>
                        </div>
                        <div className={`mt-3 text-xs px-2 py-1 rounded-lg w-fit ${
                            forecastSummary.trend === 'growing' ? 'bg-success/10 text-success' :
                            forecastSummary.trend === 'declining' ? 'bg-error/10 text-error' :
                            'bg-warning/10 text-warning'
                        }`}>
                            {forecastSummary.trend === 'growing' ? '📈 نمو' : forecastSummary.trend === 'declining' ? '📉 انخفاض' : '➡️ مستقر'}
                        </div>
                    </motion.div>
                )}

                {/* Anomaly Indicators */}
                {anomalies.length > 0 && (
                    <motion.div variants={item} className="glass-panel rounded-3xl p-6 border border-warning/20">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-bold text-heading flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4 text-warning" />
                                شذوذات مكتشفة
                            </h3>
                            <span className="text-xs bg-warning/20 text-warning px-2 py-0.5 rounded-full">{anomalies.length}</span>
                        </div>
                        <div className="space-y-2">
                            {anomalies.map((a, i) => (
                                <div key={i} className={`text-xs p-2 rounded-lg border ${
                                    a.severity === 'high' ? 'border-error/30 bg-error/5 text-error' : 'border-warning/30 bg-warning/5 text-warning'
                                }`}>
                                    <p className="font-medium">{a.title}</p>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Unread Alerts Banner */}
                {unreadAlerts > 0 && (
                    <motion.div variants={item} className="col-span-1 md:col-span-2 lg:col-span-4 glass-panel rounded-2xl p-4 border border-accent/20 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center">
                                <span className="text-accent font-bold text-sm">{unreadAlerts}</span>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-heading">لديك {unreadAlerts} تنبيه جديد</p>
                                <p className="text-xs text-muted">تحقق من التنبيهات للاطلاع على التحديثات المالية</p>
                            </div>
                        </div>
                        <Link to="/alerts" className="text-xs text-accent border border-accent/30 px-3 py-1.5 rounded-lg hover:bg-accent/10 transition-colors">
                            عرض التنبيهات
                        </Link>
                    </motion.div>
                )}

                {/* AI Advisor Mini-Card */}
                {advisorScore && (
                    <motion.div variants={item} className="glass-panel rounded-3xl p-6 border border-accent/20">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-bold text-heading flex items-center gap-2">
                                <Sparkles className="w-4 h-4 text-accent" />
                                الصحة المالية
                            </h3>
                            <Link to="/advisor" className="text-xs text-accent flex items-center gap-1 hover:underline">
                                التفاصيل <ChevronRight className="w-3 h-3" />
                            </Link>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className={`text-4xl font-bold tabular-nums ${
                                advisorScore.health_score >= 70 ? 'text-success' :
                                advisorScore.health_score >= 40 ? 'text-warning' : 'text-error'
                            }`}>
                                {advisorScore.health_score}
                                <span className="text-sm font-normal text-muted">/100</span>
                            </div>
                            <div className="flex-1 space-y-1">
                                {advisorScore.action_items.slice(0, 2).map((a, i) => (
                                    <p key={i} className="text-xs text-muted truncate">• {a}</p>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}

            </motion.div>
        </div>
    )
}
