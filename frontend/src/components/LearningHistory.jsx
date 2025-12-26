import { X, Clock } from 'lucide-react'

function LearningHistory({ history, onClose, onSelectEntry }) {
    // Format relative time
    const formatRelativeTime = (date) => {
        const now = new Date()
        const diff = now - new Date(date)

        const minutes = Math.floor(diff / 60000)
        const hours = Math.floor(diff / 3600000)
        const days = Math.floor(diff / 86400000)

        if (minutes < 1) return 'Just now'
        if (minutes < 60) return `${minutes}m ago`
        if (hours < 24) return `${hours}h ago`
        return `${days}d ago`
    }

    // Format timestamp as MM:SS
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60)
        const secs = Math.floor(seconds % 60)
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    return (
        <>
            <div className="history-overlay" onClick={onClose} />
            <div className="history-panel">
                <div className="history-header">
                    <h2>Learning History</h2>
                    <button className="history-close-btn" onClick={onClose}>
                        <X size={18} />
                    </button>
                </div>

                <div className="history-list">
                    {history.length === 0 ? (
                        <div className="history-empty">
                            <Clock size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                            <p>No learning history yet.</p>
                            <p>Pause a video to get explanations!</p>
                        </div>
                    ) : (
                        history.map((entry) => (
                            <div
                                key={entry.id}
                                className="history-item"
                                onClick={() => onSelectEntry(entry)}
                            >
                                <div className="history-item-header">
                                    <span className="history-item-topic">
                                        {entry.topic || 'Explanation'}
                                    </span>
                                    <span className="history-item-time">
                                        {formatRelativeTime(entry.createdAt)}
                                    </span>
                                </div>
                                <div className="history-item-summary">
                                    {entry.summary || `At ${formatTime(entry.timestamp)}`}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </>
    )
}

export default LearningHistory
