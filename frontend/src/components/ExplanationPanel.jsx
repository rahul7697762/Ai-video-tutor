import { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Lightbulb, Play, Pause, Volume2, Send, MessageCircle } from 'lucide-react'

function ExplanationPanel({ explanation, isLoading, error, timestamp, onAskFollowup }) {
    const [isPlaying, setIsPlaying] = useState(false)
    const [chatInput, setChatInput] = useState('')
    const audioRef = useRef(null)
    const chatInputRef = useRef(null)

    // Handle chat submission
    const handleChatSubmit = (e) => {
        e.preventDefault()
        if (chatInput.trim() && !isLoading) {
            onAskFollowup(chatInput.trim())
            setChatInput('')
        }
    }

    // Format timestamp as MM:SS
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    // Handle audio playback
    const toggleAudio = () => {
        if (!audioRef.current) return

        if (isPlaying) {
            audioRef.current.pause()
        } else {
            audioRef.current.play()
        }
        setIsPlaying(!isPlaying)
    }

    const handleAudioEnded = () => {
        setIsPlaying(false)
    }

    // Empty state
    if (!explanation && !isLoading && !error) {
        return (
            <div className="explanation-panel">
                <div className="panel-header">
                    <div className="panel-title">
                        <Lightbulb size={20} />
                        AI Tutor
                    </div>
                </div>
                <div className="panel-content">
                    <div className="panel-empty">
                        <div className="empty-icon">🎬</div>
                        <h3>Ready to Help!</h3>
                        <p>Pause the video whenever you don't understand something, or ask a question below anytime.</p>
                    </div>
                </div>
                <div className="chat-input-container">
                    <form className="chat-input-form" onSubmit={handleChatSubmit}>
                        <MessageCircle size={20} className="chat-icon" />
                        <input
                            ref={chatInputRef}
                            type="text"
                            className="chat-input"
                            placeholder="Ask anything about the video..."
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            className="chat-send-btn"
                            disabled={!chatInput.trim() || isLoading}
                        >
                            <Send size={18} />
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    // Loading state
    if (isLoading) {
        return (
            <div className="explanation-panel">
                <div className="panel-header">
                    <div className="panel-title">
                        <Lightbulb size={20} />
                        AI Tutor
                        <span className="panel-timestamp">at {formatTime(timestamp)}</span>
                    </div>
                </div>
                <div className="panel-content">
                    <div className="panel-loading">
                        <div className="loading-animation">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <p>Analyzing context and generating explanation...</p>
                    </div>
                </div>
                <div className="chat-input-container">
                    <form className="chat-input-form" onSubmit={handleChatSubmit}>
                        <MessageCircle size={20} className="chat-icon" />
                        <input
                            type="text"
                            className="chat-input"
                            placeholder="Ask anything about the video..."
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            disabled={true}
                        />
                        <button
                            type="submit"
                            className="chat-send-btn"
                            disabled={true}
                        >
                            <Send size={18} />
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    // Error state
    if (error) {
        return (
            <div className="explanation-panel">
                <div className="panel-header">
                    <div className="panel-title">
                        <Lightbulb size={20} />
                        AI Tutor
                    </div>
                </div>
                <div className="panel-content">
                    <div className="panel-error">
                        <div className="error-icon">😕</div>
                        <h3>Couldn't Generate Explanation</h3>
                        <p>{error}</p>
                    </div>
                </div>
                <div className="chat-input-container">
                    <form className="chat-input-form" onSubmit={handleChatSubmit}>
                        <MessageCircle size={20} className="chat-icon" />
                        <input
                            ref={chatInputRef}
                            type="text"
                            className="chat-input"
                            placeholder="Try asking a different question..."
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            className="chat-send-btn"
                            disabled={!chatInput.trim() || isLoading}
                        >
                            <Send size={18} />
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    // Content state
    return (
        <div className="explanation-panel">
            <div className="panel-header">
                <div className="panel-title">
                    <Lightbulb size={20} />
                    AI Tutor
                    <span className="panel-timestamp">at {formatTime(explanation.timestamp)}</span>
                </div>
                {explanation.processing_time_ms && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {(explanation.processing_time_ms / 1000).toFixed(1)}s
                    </span>
                )}
            </div>

            <div className="panel-content">
                <div className="explanation-content">
                    {/* Summary */}
                    {explanation.summary && (
                        <div className="explanation-summary">
                            <h4>Quick Summary</h4>
                            <p>{explanation.summary}</p>
                        </div>
                    )}

                    {/* Main Explanation */}
                    <div className="explanation-body">
                        <ReactMarkdown>
                            {explanation.explanation}
                        </ReactMarkdown>
                    </div>

                    {/* Audio Player */}
                    {explanation.audio_url && (
                        <div className="audio-player">
                            <button className="audio-btn" onClick={toggleAudio}>
                                {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                            </button>
                            <div className="audio-label">
                                <span>Listen to Explanation</span>
                                {explanation.audio_duration && (
                                    <span style={{ fontWeight: 'normal' }}>
                                        {Math.round(explanation.audio_duration)}s
                                    </span>
                                )}
                            </div>
                            <Volume2 size={18} style={{ color: 'var(--text-muted)' }} />
                            <audio
                                ref={audioRef}
                                src={explanation.audio_url}
                                onEnded={handleAudioEnded}
                                style={{ display: 'none' }}
                            />
                        </div>
                    )}

                    {/* Retrieved Context Indicators */}
                    {explanation.retrieved_chunks && explanation.retrieved_chunks.length > 0 && (
                        <div className="context-chips">
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: '100%', marginBottom: '4px' }}>
                                Context sources:
                            </span>
                            {explanation.retrieved_chunks.slice(0, 5).map((chunk, i) => (
                                <span
                                    key={i}
                                    className={`context-chip ${chunk.relevance_type}`}
                                    title={chunk.text}
                                >
                                    {chunk.relevance_type === 'temporal' && '⏱️'}
                                    {chunk.relevance_type === 'foundational' && '📚'}
                                    {chunk.relevance_type === 'semantic' && '🔗'}
                                    {formatTime(chunk.start_time)}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="chat-input-container">
                <form className="chat-input-form" onSubmit={handleChatSubmit}>
                    <MessageCircle size={20} className="chat-icon" />
                    <input
                        ref={chatInputRef}
                        type="text"
                        className="chat-input"
                        placeholder="Ask a follow-up question..."
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        className="chat-send-btn"
                        disabled={!chatInput.trim() || isLoading}
                    >
                        <Send size={18} />
                    </button>
                </form>
            </div>
        </div>
    )
}

export default ExplanationPanel
