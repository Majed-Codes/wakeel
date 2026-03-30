import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Minus, AlertTriangle, Lightbulb, Calendar } from 'lucide-react'
import { motion } from 'framer-motion'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { forecastAPI } from '../api'

interface ForecastPoint {
    date: string
    value: number
    lower: number
    upper: number
}

interface ForecastData {
    period_days: number
    revenue_forecast: ForecastPoint[]
    expense_forecast: ForecastPoint[]
    net_forecast: ForecastPoint[]
    summary: {
        avg_daily_revenue: number
        avg_daily_expense: number
        predicted_net_30d: number
        trend: string
        risk_level: string
    }
}

interface Insights {
    trend: string
    seasonal_patterns: string[]
    risk_factors: string[]
    recommendations: string[]
}

const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.08 } },
}
const item = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0 },
}

export default function ForecastPage() {
    const [forecast, setForecast] = useState<ForecastData | null>(null)
    const [insights, setInsights] = useState<Insights | null>(null)
    const [period, setPeriod] = useState(30)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadForecast()
    }, [period])

    const loadForecast = async () => {
        setLoading(true)
        try {
            const [fRes, iRes] = await Promise.all([
                forecastAPI.get(period),
                forecastAPI.insights(),
            ])
            setForecast(fRes.data)
            setInsights(iRes.data)
        } catch {
            // error
        } finally {
            setLoading(false)
        }
    }

    // Merge revenue + expense + net into single chart data
    const chartData = forecast
        ? forecast.revenue_forecast.map((r, i) => ({
            date: r.date.slice(5), // MM-DD
            revenue: Math.round(r.value),
            expenses: Math.round(forecast.expense_forecast[i]?.value || 0),
            net: Math.round(forecast.net_forecast[i]?.value || 0),
            revUpper: Math.round(r.upper),
            revLower: Math.round(r.lower),
        }))
        : []

    const trendIcon = forecast?.summary?.trend === 'growing'
        ? <TrendingUp className="text-success" />
        : forecast?.summary?.trend === 'declining'
            ? <TrendingDown className="text-error" />
            : <Minus className="text-warning" />

    const trendLabel = forecast?.summary?.trend === 'growing' ? 'نمو'
        : forecast?.summary?.trend === 'declining' ? 'انخفاض' : 'مستقر'

    const riskColor = forecast?.summary?.risk_level === 'high' ? 'text-error'
        : forecast?.summary?.risk_level === 'medium' ? 'text-warning' : 'text-success'

    const riskLabel = forecast?.summary?.risk_level === 'high' ? 'مرتفع'
        : forecast?.summary?.risk_level === 'medium' ? 'متوسط' : 'منخفض'

    return (
        <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
            {/* Header */}
            <motion.div variants={item} className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-heading">التنبؤ المالي</h1>
                    <p className="text-sm text-body mt-1">توقعات التدفق النقدي بناءً على بياناتك التاريخية</p>
                </div>
                <div className="flex gap-2">
                    {[30, 60, 90].map(d => (
                        <button
                            key={d}
                            onClick={() => setPeriod(d)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${period === d
                                ? 'bg-accent text-white shadow-glow'
                                : 'bg-glass border border-glass-border text-muted hover:text-white'
                                }`}
                        >
                            {d} يوم
                        </button>
                    ))}
                </div>
            </motion.div>

            {loading ? (
                <div className="h-96 flex items-center justify-center">
                    <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                </div>
            ) : !forecast ? (
                <div className="h-96 flex flex-col items-center justify-center gap-4 text-center">
                    <TrendingUp size={48} className="text-muted opacity-30" />
                    <p className="text-muted">تعذّر تحميل بيانات التنبؤ</p>
                    <button onClick={loadForecast} className="px-4 py-2 bg-accent text-white rounded-xl text-sm">إعادة المحاولة</button>
                </div>
            ) : (
                <>
                    {/* Summary Cards */}
                    <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.05 }} className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="glass-panel p-5 rounded-2xl">
                            <p className="text-xs text-muted mb-1">متوسط الإيراد اليومي</p>
                            <p className="text-2xl font-bold text-success">
                                {forecast.summary.avg_daily_revenue.toLocaleString('ar-SA')} <span className="text-sm text-muted">ر.س</span>
                            </p>
                        </div>
                        <div className="glass-panel p-5 rounded-2xl">
                            <p className="text-xs text-muted mb-1">متوسط المصروف اليومي</p>
                            <p className="text-2xl font-bold text-error">
                                {forecast.summary.avg_daily_expense.toLocaleString('ar-SA')} <span className="text-sm text-muted">ر.س</span>
                            </p>
                        </div>
                        <div className="glass-panel p-5 rounded-2xl">
                            <p className="text-xs text-muted mb-1">صافي الـ 30 يوم القادمة</p>
                            <p className="text-2xl font-bold text-heading">
                                {forecast.summary.predicted_net_30d.toLocaleString('ar-SA')} <span className="text-sm text-muted">ر.س</span>
                            </p>
                        </div>
                        <div className="glass-panel p-5 rounded-2xl flex items-center justify-between">
                            <div>
                                <p className="text-xs text-muted mb-1">الاتجاه</p>
                                <p className="text-lg font-bold text-heading">{trendLabel}</p>
                                <p className={`text-xs ${riskColor}`}>مخاطر: {riskLabel}</p>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-glass border border-glass-border flex items-center justify-center">
                                {trendIcon}
                            </div>
                        </div>
                    </motion.div>

                    {/* Forecast Chart */}
                    <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.13 }} className="glass-panel p-6 rounded-2xl">
                        <h3 className="text-lg font-bold text-heading mb-4 flex items-center gap-2">
                            <Calendar className="w-5 h-5 text-accent" />
                            توقعات {period} يوم
                        </h3>
                        <ResponsiveContainer width="100%" height={350}>
                            <AreaChart data={chartData}>
                                <defs>
                                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#34C759" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#34C759" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="expGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#FF3B30" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#FF3B30" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="netGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#2F80ED" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#2F80ED" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="date" stroke="#71717A" fontSize={11} />
                                <YAxis stroke="#71717A" fontSize={11} />
                                <Tooltip
                                    contentStyle={{ background: '#1a1a1e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', fontSize: '12px' }}
                                    labelStyle={{ color: '#A1A1AA' }}
                                />
                                <Legend />
                                <Area type="monotone" dataKey="revenue" name="الإيرادات" stroke="#34C759" fill="url(#revGrad)" strokeWidth={2} />
                                <Area type="monotone" dataKey="expenses" name="المصاريف" stroke="#FF3B30" fill="url(#expGrad)" strokeWidth={2} />
                                <Area type="monotone" dataKey="net" name="الصافي" stroke="#2F80ED" fill="url(#netGrad)" strokeWidth={2} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </motion.div>

                    {/* Insights */}
                    {insights && (
                        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.21 }} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Risk Factors */}
                            <div className="glass-panel p-6 rounded-2xl">
                                <h3 className="text-base font-bold text-heading mb-3 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-warning" />
                                    عوامل المخاطر
                                </h3>
                                <div className="space-y-2">
                                    {insights.risk_factors.length > 0 ? insights.risk_factors.map((r, i) => (
                                        <div key={i} className="flex gap-2 text-sm text-body">
                                            <span className="text-warning shrink-0">!</span>
                                            <span>{r}</span>
                                        </div>
                                    )) : (
                                        <p className="text-sm text-muted">لا توجد مخاطر حالياً</p>
                                    )}
                                </div>
                            </div>

                            {/* Recommendations */}
                            <div className="glass-panel p-6 rounded-2xl">
                                <h3 className="text-base font-bold text-heading mb-3 flex items-center gap-2">
                                    <Lightbulb className="w-4 h-4 text-accent" />
                                    التوصيات
                                </h3>
                                <div className="space-y-2">
                                    {insights.recommendations.length > 0 ? insights.recommendations.map((r, i) => (
                                        <div key={i} className="flex gap-2 text-sm text-body">
                                            <span className="text-accent shrink-0">*</span>
                                            <span>{r}</span>
                                        </div>
                                    )) : (
                                        <p className="text-sm text-muted">لا توجد توصيات حالياً</p>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </>
            )}
        </motion.div>
    )
}
