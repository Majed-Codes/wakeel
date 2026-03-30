import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import VoicePage from './pages/VoicePage'
import ChatPage from './pages/ChatPage'
import CompliancePage from './pages/CompliancePage'
import ForecastPage from './pages/ForecastPage'
import UploadPage from './pages/UploadPage'
import ReportsPage from './pages/ReportsPage'
import AlertsPage from './pages/AlertsPage'
import WhatsAppPage from './pages/WhatsAppPage'
import LoginPage from './pages/LoginPage'
import BudgetPage from './pages/BudgetPage'
import ZakatPage from './pages/ZakatPage'
import VendorsPage from './pages/VendorsPage'
import PayrollPage from './pages/PayrollPage'
import AdvisorPage from './pages/AdvisorPage'
import { authAPI } from './api'

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('wakeel_token'))
  const location = useLocation()

  useEffect(() => {
    if (token) {
      authAPI.getProfile()
        .then(() => localStorage.setItem('wakeel_token', token))
        .catch(() => handleLogout())
    }
  }, [token])

  const handleLogin = () => {
    setToken(localStorage.getItem('wakeel_token'))
  }

  const handleLogout = () => {
    localStorage.removeItem('wakeel_token')
    setToken(null)
  }

  if (!token) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <div className="min-h-screen bg-bg text-heading font-sans selection:bg-accent/30 selection:text-white">
      <Sidebar onLogout={handleLogout} />

      <main className="pt-16 lg:pt-6 pb-6 pl-4 pr-[72px] lg:pr-[104px] lg:pl-6 min-h-screen">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<PageWrapper><Dashboard /></PageWrapper>} />
            <Route path="/voice" element={<PageWrapper><VoicePage /></PageWrapper>} />
            <Route path="/chat" element={<PageWrapper><ChatPage /></PageWrapper>} />
            <Route path="/compliance" element={<PageWrapper><CompliancePage /></PageWrapper>} />
            <Route path="/forecast" element={<PageWrapper><ForecastPage /></PageWrapper>} />
            <Route path="/upload" element={<PageWrapper><UploadPage /></PageWrapper>} />
            <Route path="/reports" element={<PageWrapper><ReportsPage /></PageWrapper>} />
            <Route path="/alerts" element={<PageWrapper><AlertsPage /></PageWrapper>} />
            <Route path="/whatsapp" element={<PageWrapper><WhatsAppPage /></PageWrapper>} />
            {/* New routes */}
            <Route path="/budget" element={<PageWrapper><BudgetPage /></PageWrapper>} />
            <Route path="/zakat" element={<PageWrapper><ZakatPage /></PageWrapper>} />
            <Route path="/vendors" element={<PageWrapper><VendorsPage /></PageWrapper>} />
            <Route path="/payroll" element={<PageWrapper><PayrollPage /></PageWrapper>} />
            <Route path="/advisor" element={<PageWrapper><AdvisorPage /></PageWrapper>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
      </main>
    </div>
  )
}

function PageWrapper({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.98 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="w-full max-w-7xl mx-auto"
    >
      {children}
    </motion.div>
  )
}
