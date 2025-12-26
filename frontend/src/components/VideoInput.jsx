import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'

function VideoInput({ onSubmit, status, message }) {
    const [url, setUrl] = useState('')

    const handleSubmit = (e) => {
        e.preventDefault()
        if (url.trim() && status !== 'loading') {
            onSubmit(url.trim())
        }
    }

    return (
        <div className="video-input-container">
            <form onSubmit={handleSubmit}>
                <div className="video-input-wrapper">
                    <input
                        type="text"
                        className="video-input"
                        placeholder="Paste a YouTube video URL..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        disabled={status === 'loading'}
                    />
                    <button
                        type="submit"
                        className="video-submit-btn"
                        disabled={!url.trim() || status === 'loading'}
                    >
                        {status === 'loading' ? (
                            <Loader2 size={20} className="animate-spin" />
                        ) : (
                            <Search size={20} />
                        )}
                        <span>Start Learning</span>
                    </button>
                </div>
            </form>

            {message && (
                <div className={`input-status ${status}`}>
                    {status === 'loading' && <span className="animate-pulse">⏳ </span>}
                    {status === 'ready' && '✅ '}
                    {status === 'error' && '❌ '}
                    {message}
                </div>
            )}
        </div>
    )
}

export default VideoInput
