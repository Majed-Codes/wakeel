import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { Mic, Square, Upload, CheckCircle2, AlertCircle } from 'lucide-react'
import { transactionsAPI } from '../api'

export default function VoicePage() {
    const [isRecording, setIsRecording] = useState(false)
    const [transcribing, setTranscribing] = useState(false)
    const [result, setResult] = useState<any>(null)
    const fileInput = useRef<HTMLInputElement>(null)

    const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        setTranscribing(true)
        try {
            const res = await transactionsAPI.voiceUpload(file)
            setResult(res.data)
        } catch (err) {
            console.error(err)
        } finally {
            setTranscribing(false)
        }
    }

    return (
        <div className="max-w-xl mx-auto py-12 text-center">
            <h1 className="text-3xl font-bold text-heading mb-2">تسجيل معاملة</h1>
            <p className="text-body mb-12">تحدث لوصف معاملة مالية، وسيقوم وكيل بتحليلها وتسجيلها فوراً.</p>

            {/* Siri Orb / Recording Button */}
            <div className="relative inline-flex justify-center items-center mb-12 group">
                {/* Glow Effects */}
                <div className={`absolute inset-0 rounded-full blur-[60px] transition-all duration-500 ${isRecording ? 'bg-error/30 scale-150' : 'bg-accent/20 scale-100 group-hover:scale-125 group-hover:bg-accent/30'}`} />

                <button
                    onClick={() => setIsRecording(!isRecording)}
                    className={`
                        relative z-10 w-32 h-32 rounded-full flex items-center justify-center
                        transition-all duration-500 shadow-glow border-4
                        ${isRecording
                            ? 'bg-error text-white border-error scale-110'
                            : 'bg-glass backdrop-blur-3xl border-accent/30 text-accent hover:border-accent hover:scale-105'}
                    `}
                >
                    {isRecording ? (
                        <Square fill="currentColor" className="w-10 h-10" />
                    ) : (
                        <Mic className="w-12 h-12" />
                    )}
                </button>

                {/* Pulse Rings */}
                {isRecording && (
                    <>
                        <motion.div
                            initial={{ scale: 1, opacity: 0.5 }}
                            animate={{ scale: 2, opacity: 0 }}
                            transition={{ repeat: Infinity, duration: 1.5 }}
                            className="absolute inset-0 rounded-full border border-error"
                        />
                        <motion.div
                            initial={{ scale: 1, opacity: 0.5 }}
                            animate={{ scale: 2.5, opacity: 0 }}
                            transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }}
                            className="absolute inset-0 rounded-full border border-error"
                        />
                    </>
                )}
            </div>

            {/* Actions */}
            <div className="flex justify-center gap-4 mb-12">
                <button
                    onClick={() => fileInput.current?.click()}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl bg-glass border border-glass-border hover:bg-glass-hover transition-colors text-sm font-medium"
                >
                    <Upload size={18} />
                    رفع ملف صوتي
                </button>
                <input ref={fileInput} type="file" hidden accept="audio/*" onChange={handleFile} />
            </div>

            {/* Result Area */}
            {transcribing && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel p-8 rounded-2xl">
                    <div className="flex items-center justify-center gap-3">
                        <div className="w-2 h-2 bg-accent rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-accent rounded-full animate-bounce delay-100" />
                        <div className="w-2 h-2 bg-accent rounded-full animate-bounce delay-200" />
                    </div>
                    <p className="text-sm text-muted mt-4">جاري تحليل الصوت وتصنيف المعاملة...</p>
                </motion.div>
            )}

            {result && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel p-6 rounded-3xl text-right border-l-4 border-l-success"
                >
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-success/10 rounded-full text-success shrink-0">
                            <CheckCircle2 />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-bold text-heading text-lg mb-1">تم تسجيل المعاملة بنجاح</h3>
                            <p className="text-body text-sm mb-4">"{result.transaction?.raw_transcription || 'تم استخراج البيانات'}"</p>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-black/20 p-3 rounded-xl">
                                    <span className="text-xs text-muted block mb-1">المبلغ</span>
                                    <span className="text-xl font-bold text-white tabular-nums">{result.extracted_data?.amount} ر.س</span>
                                </div>
                                <div className="bg-black/20 p-3 rounded-xl">
                                    <span className="text-xs text-muted block mb-1">التصنيف</span>
                                    <span className="text-sm font-medium text-white">{result.extracted_data?.category}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            )}
        </div>
    )
}
