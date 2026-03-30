import { useState, useEffect } from 'react'
import { Bell, BellOff, AlertTriangle, TrendingDown, ShieldAlert, DollarSign, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'
import { alertsAPI } from '../api'

interface Alert {
    id: number
    type: string
    title: string
    message: string
    severity: string
    is_read: boolean
    created_at: string
}

const SEVERITY_STYLES: Record<string, string> = {
    critical: 'border-error/40 bg-error/10',
    high: 'border-warning/40 bg-warning/10',
    medium: 'border-accent/40 bg-accent/10',
    low: 'border-glass-border bg-glass',
}

const SEVERITY_DOT: Record<string, string> = {
    critical: 'bg-error',
    high: 'bg-warning',
    medium: 'bg-accent',
    low: 'bg-muted',
}

const TYPE_ICONS: Record<string, React.ElementType> = {
    budget_exceeded: DollarSign,
    unusual_spending: AlertTriangle,
    revenue_drop: TrendingDown,
    anomaly_detected: AlertTriangle,
    compliance_due: ShieldAlert,
    forecast_warning: TrendingDown,
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }
const item = { hidden: { opacity: 0, x: 20 }, show: { opacity: 1, x: 0 } }

// Mock alerts for display until backend alerts endpoint is wired up
const MOCK_ALERTS: Alert[] = [
    {
        id: 1,
        type: 'revenue_drop',
        title: 'انخفاض في الإيرادات',
        message: 'انخفضت إيرادات هذا الشهر بنسبة 22% مقارنةً بالشهر الماضي. راجع مصادر الدخل.',
        severity: 'high',
        is_read: false,
        created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
        id: 2,
        type: 'unusual_spending',
        title: 'إنفاق غير اعتيادي',
        message: 'تم رصد معاملة بقيمة 45,000 ر.س مع جهة لم تتعامل معها من قبل.',
        severity: 'medium',
        is_read: false,
        created_at: new Date(Date.now() - 7200000).toISOString(),
    },
    {
        id: 3,
        type: 'forecast_warning',
        title: 'تحذير من التنبؤ المالي',
        message: 'يتوقع النظام تراجعاً في صافي التدفق النقدي خلال الـ 30 يوماً القادمة.',
        severity: 'medium',
        is_read: true,
        created_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
        id: 4,
        type: 'compliance_due',
        title: 'موعد الإقرار الضريبي',
        message: 'اقترب موعد تقديم الإقرار الضريبي لشهر يناير. تأكد من اكتمال بياناتك.',
        severity: 'low',
        is_read: true,
        created_at: new Date(Date.now() - 172800000).toISOString(),
    },
]

function timeAgo(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime()
    const hours = Math.floor(diff / 3600000)
    if (hours < 1) return 'منذ قليل'
    if (hours < 24) return `منذ ${hours} ساعة`
    return `منذ ${Math.floor(hours / 24)} يوم`
}

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Alert[]>(MOCK_ALERTS)
    const [filter, setFilter] = useState<'all' | 'unread'>('all')

    const markRead = async (id: number) => {
        setAlerts(a => a.map(alert => alert.id === id ? { ...alert, is_read: true } : alert))
        try { await alertsAPI.markRead(id) } catch { /* backend may not be wired yet */ }
    }

    const markAllRead = () => {
        setAlerts(a => a.map(alert => ({ ...alert, is_read: true })))
    }

    const displayed = filter === 'unread' ? alerts.filter(a => !a.is_read) : alerts
    const unreadCount = alerts.filter(a => !a.is_read).length

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-heading flex items-center gap-2">
                        التنبيهات
                        {unreadCount > 0 && (
                            <span className="text-sm font-medium px-2 py-0.5 bg-error text-white rounded-full">
                                {unreadCount}
                            </span>
                        )}
                    </h1>
                    <p className="text-sm text-body mt-1">تنبيهات ذكية بناءً على بياناتك المالية</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setFilter(f => f === 'all' ? 'unread' : 'all')}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all border
                            ${filter === 'unread'
                                ? 'bg-accent text-white border-accent'
                                : 'bg-glass border-glass-border text-muted hover:text-white'
                            }`}
                    >
                        {filter === 'unread' ? 'الكل' : 'غير مقروء فقط'}
                    </button>
                    {unreadCount > 0 && (
                        <button
                            onClick={markAllRead}
                            className="px-4 py-2 rounded-xl text-sm text-muted hover:text-white border border-glass-border bg-glass transition-colors"
                        >
                            تحديد الكل كمقروء
                        </button>
                    )}
                </div>
            </div>

            {/* Alerts List */}
            {displayed.length === 0 ? (
                <div className="glass-card p-16 rounded-2xl text-center space-y-4">
                    <BellOff className="w-12 h-12 text-muted mx-auto" />
                    <p className="text-heading font-medium">لا توجد تنبيهات</p>
                    <p className="text-sm text-muted">سيتم إشعارك عند اكتشاف أي تغييرات مالية مهمة</p>
                </div>
            ) : (
                <motion.div variants={container} initial="hidden" animate="show" className="space-y-3">
                    {displayed.map(alert => {
                        const Icon = TYPE_ICONS[alert.type] || Bell
                        return (
                            <motion.div
                                key={alert.id}
                                variants={item}
                                className={`
                                    relative p-5 rounded-2xl border cursor-pointer transition-all
                                    ${SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.low}
                                    ${!alert.is_read ? 'ring-1 ring-accent/30' : 'opacity-70'}
                                `}
                                onClick={() => !alert.is_read && markRead(alert.id)}
                            >
                                {/* Unread indicator */}
                                {!alert.is_read && (
                                    <span className={`absolute top-4 left-4 w-2 h-2 rounded-full ${SEVERITY_DOT[alert.severity] || 'bg-accent'}`} />
                                )}

                                <div className="flex items-start gap-4">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0
                                        ${alert.severity === 'critical' ? 'bg-error/20' :
                                          alert.severity === 'high' ? 'bg-warning/20' :
                                          alert.severity === 'medium' ? 'bg-accent/20' : 'bg-glass'}`}>
                                        <Icon className={`w-5 h-5
                                            ${alert.severity === 'critical' ? 'text-error' :
                                              alert.severity === 'high' ? 'text-warning' :
                                              alert.severity === 'medium' ? 'text-accent' : 'text-muted'}`} />
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-2 mb-1">
                                            <h3 className={`text-sm font-semibold ${alert.is_read ? 'text-body' : 'text-heading'}`}>
                                                {alert.title}
                                            </h3>
                                            <span className="text-xs text-muted shrink-0">{timeAgo(alert.created_at)}</span>
                                        </div>
                                        <p className="text-xs text-body leading-relaxed">{alert.message}</p>
                                    </div>

                                    {alert.is_read && (
                                        <CheckCircle2 className="w-4 h-4 text-muted shrink-0 mt-0.5" />
                                    )}
                                </div>
                            </motion.div>
                        )
                    })}
                </motion.div>
            )}
        </div>
    )
}
