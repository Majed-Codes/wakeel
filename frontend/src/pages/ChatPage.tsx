import { useState, useRef, useEffect, useMemo } from 'react'
import { Send, Bot, User, Sparkles } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { chatAPI } from '../api'

/** Lightweight markdown renderer for chat messages (bold, newlines, lists) */
function FormattedMessage({ content }: { content: string }) {
    const parts = useMemo(() => {
        // Split by **bold** markers
        const segments = content.split(/(\*\*[^*]+\*\*)/g)
        return segments.map((seg, i) => {
            if (seg.startsWith('**') && seg.endsWith('**')) {
                return <strong key={i} className="font-bold">{seg.slice(2, -2)}</strong>
            }
            return <span key={i}>{seg}</span>
        })
    }, [content])

    // Split by newlines, render each line
    const lines = content.split('\n')

    return (
        <div className="space-y-1.5">
            {lines.map((line, li) => {
                const trimmed = line.trim()
                // List items (- or •)
                const isList = trimmed.startsWith('- ') || trimmed.startsWith('• ')
                const lineContent = isList ? trimmed.slice(2) : line

                // Bold rendering within a line
                const segments = lineContent.split(/(\*\*[^*]+\*\*)/g)
                const rendered = segments.map((seg, si) => {
                    if (seg.startsWith('**') && seg.endsWith('**')) {
                        return <strong key={si} className="font-semibold">{seg.slice(2, -2)}</strong>
                    }
                    return <span key={si}>{seg}</span>
                })

                if (isList) {
                    return (
                        <div key={li} className="flex gap-1.5 mr-2">
                            <span className="text-accent shrink-0">•</span>
                            <span>{rendered}</span>
                        </div>
                    )
                }

                if (trimmed === '') return <div key={li} className="h-1.5" />

                return <div key={li}>{rendered}</div>
            })}
        </div>
    )
}

export default function ChatPage() {
    const [messages, setMessages] = useState<any[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const endRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => endRef.current?.scrollIntoView({ behavior: 'smooth' })
    useEffect(scrollToBottom, [messages])

    const send = async () => {
        if (!input.trim()) return
        const msg = { role: 'user', content: input, created_at: new Date().toISOString() }
        setMessages(p => [...p, msg])
        setInput('')
        setLoading(true)

        try {
            const res = await chatAPI.send(msg.content)
            setMessages(p => [...p, { role: 'assistant', content: res.data.content, created_at: new Date().toISOString() }])
        } catch {
            // error
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="h-[calc(100vh-140px)] flex flex-col">
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center shadow-glow mb-6">
                            <Sparkles className="text-white w-8 h-8" />
                        </div>
                        <h2 className="text-xl font-bold text-heading">كيف يمكنني مساعدتك اليوم؟</h2>
                        <p className="text-sm text-body mt-2">اسأل عن تقاريرك المالية، تحليل المصاريف، أو النصائح الضريبية</p>
                    </div>
                )}

                <AnimatePresence>
                    {messages.map((m, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            className={`flex gap-4 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
                        >
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 border border-glass-border ${m.role === 'assistant' ? 'bg-gradient-to-br from-accent to-blue-600 shadow-glow' : 'bg-glass'
                                }`}>
                                {m.role === 'assistant' ? <Bot size={20} className="text-white" /> : <User size={20} className="text-muted" />}
                            </div>

                            <div className={`
                                max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed shadow-sm relative
                                ${m.role === 'assistant'
                                    ? 'bg-glass-panel text-white rounded-tr-none border-glass-border'
                                    : 'bg-[#2F80ED] text-white rounded-tl-none shadow-glow border border-blue-400/20'}
                            `}>
                                {m.role === 'assistant' ? <FormattedMessage content={m.content} /> : m.content}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {loading && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent to-blue-600 flex items-center justify-center shrink-0">
                            <Bot size={20} className="text-white" />
                        </div>
                        <div className="bg-glass-panel p-4 rounded-2xl rounded-tr-none flex gap-1 items-center h-12">
                            <span className="w-2 h-2 bg-white/50 rounded-full animate-bounce" />
                            <span className="w-2 h-2 bg-white/50 rounded-full animate-bounce delay-100" />
                            <span className="w-2 h-2 bg-white/50 rounded-full animate-bounce delay-200" />
                        </div>
                    </motion.div>
                )}
                <div ref={endRef} />
            </div>

            {/* Input Area */}
            <div className="mt-4 glass-panel p-2 rounded-2xl flex items-center gap-2">
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && send()}
                    placeholder="اكتب رسالتك..."
                    className="flex-1 bg-transparent border-none px-4 py-3 text-white placeholder:text-muted focus:ring-0"
                    style={{ backgroundColor: 'transparent' }} // Override global input style
                />
                <button
                    onClick={send}
                    disabled={!input.trim()}
                    className="p-3 bg-accent hover:bg-accent-hover text-white rounded-xl transition-all shadow-glow disabled:opacity-50 disabled:shadow-none"
                >
                    <Send size={20} />
                </button>
            </div>
        </div>
    )
}
