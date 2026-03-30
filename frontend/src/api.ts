import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('wakeel_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Auth API
export const authAPI = {
    register: (data: { name: string; phone: string; password: string; email?: string }) =>
        api.post('/api/v1/auth/register', data),
    login: (data: { phone: string; password: string }) =>
        api.post('/api/v1/auth/login', data),
    getProfile: () => api.get('/api/v1/auth/me'),
};

// Transactions API
export const transactionsAPI = {
    list: (skip = 0, limit = 50) =>
        api.get(`/api/v1/transactions/?skip=${skip}&limit=${limit}`),
    create: (data: { amount: number; category?: string; description?: string; vendor?: string }) =>
        api.post('/api/v1/transactions/', data),
    voiceUpload: (file: File) => {
        const formData = new FormData();
        formData.append('audio', file);
        return api.post('/api/v1/transactions/voice', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
    delete: (id: number) => api.delete(`/api/v1/transactions/${id}`),
};

// Chat API
export const chatAPI = {
    send: (message: string) => api.post('/api/v1/chat/', { message }),
    history: (limit = 50) => api.get(`/api/v1/chat/history?limit=${limit}`),
};

// Compliance API
export const complianceAPI = {
    validate: (data: Record<string, unknown>) =>
        api.post('/api/v1/compliance/validate', data),
};

// Dashboard API
export const dashboardAPI = {
    summary: () => api.get('/api/v1/dashboard/'),
};

// Forecast API
export const forecastAPI = {
    get: (periodDays = 30) => api.get(`/api/v1/forecast/?period_days=${periodDays}`),
    insights: () => api.get('/api/v1/forecast/insights'),
};

// Upload API (CSV/Excel)
export const uploadAPI = {
    preview: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/api/v1/upload/preview', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
    confirm: (data: { rows: Record<string, unknown>[]; column_mapping: Record<string, string> }) =>
        api.post('/api/v1/upload/confirm', data),
};

// Receipt OCR API
export const receiptAPI = {
    upload: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/api/v1/transactions/receipt', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
    },
};

// Alerts API
export const alertsAPI = {
    list: () => api.get('/api/v1/alerts/'),
    count: () => api.get('/api/v1/alerts/count'),
    markRead: (id: number) => api.patch(`/api/v1/alerts/${id}/read`),
};

// Anomalies API
export const anomaliesAPI = {
    list: () => api.get('/api/v1/anomalies/'),
    summary: () => api.get('/api/v1/anomalies/summary'),
};

// Reports API
export const reportsAPI = {
    generate: (startDate: string, endDate: string) =>
        api.post('/api/v1/reports/generate', { start_date: startDate, end_date: endDate }, {
            responseType: 'blob',
        }),
    summary: (startDate: string, endDate: string) =>
        api.get(`/api/v1/reports/summary?start_date=${startDate}&end_date=${endDate}`),
};

// WhatsApp API
export const whatsappAPI = {
    status: () => api.get('/api/v1/whatsapp/status'),
    connect: (phoneNumber: string) =>
        api.post('/api/v1/whatsapp/connect', { phone_number: phoneNumber }),
    test: (message: string, toNumber?: string) =>
        api.post('/api/v1/whatsapp/test', { message, to_number: toNumber }),
    weeklySummary: () => api.get('/api/v1/whatsapp/weekly-summary'),
    markAllRead: () => api.patch('/api/v1/alerts/read-all'),
};

// Budget API
export const budgetAPI = {
    list: (month?: number, year?: number) => {
        const params = new URLSearchParams()
        if (month) params.set('month', String(month))
        if (year) params.set('year', String(year))
        return api.get(`/api/v1/budget/?${params}`)
    },
    create: (data: { category: string; amount: number; month: number; year: number }) =>
        api.post('/api/v1/budget/', data),
    update: (id: number, data: { amount: number }) =>
        api.put(`/api/v1/budget/${id}`, data),
    delete: (id: number) => api.delete(`/api/v1/budget/${id}`),
}

// Zakat API
export const zakatAPI = {
    calculate: () => api.get('/api/v1/zakat/'),
}

// Vendors API
export const vendorsAPI = {
    list: () => api.get('/api/v1/vendors/'),
    create: (data: Record<string, unknown>) => api.post('/api/v1/vendors/', data),
    update: (id: number, data: Record<string, unknown>) => api.put(`/api/v1/vendors/${id}`, data),
    delete: (id: number) => api.delete(`/api/v1/vendors/${id}`),
    transactions: (id: number) => api.get(`/api/v1/vendors/${id}/transactions`),
}

// Payroll API
export const payrollAPI = {
    employees: () => api.get('/api/v1/payroll/employees'),
    addEmployee: (data: Record<string, unknown>) => api.post('/api/v1/payroll/employees', data),
    updateEmployee: (id: number, data: Record<string, unknown>) => api.put(`/api/v1/payroll/employees/${id}`, data),
    deleteEmployee: (id: number) => api.delete(`/api/v1/payroll/employees/${id}`),
    runPayroll: (month: number, year: number) => api.post('/api/v1/payroll/run', { month, year }),
    runs: () => api.get('/api/v1/payroll/runs'),
}

// AI Advisor API
export const advisorAPI = {
    get: () => api.get('/api/v1/advisor/'),
}

// VAT Return (extends compliance)
export const vatAPI = {
    calculate: (quarter: number, year: number) =>
        api.post('/api/v1/compliance/vat-return', { quarter, year }),
}

// Bank Statement (extends upload)
export const bankStatementAPI = {
    upload: (file: File) => {
        const formData = new FormData()
        formData.append('file', file)
        return api.post('/api/v1/upload/bank-statement', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
    },
}

export default api;

