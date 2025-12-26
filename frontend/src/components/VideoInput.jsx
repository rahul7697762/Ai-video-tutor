import { useState, useRef } from 'react'
import { Search, Loader2, Upload, FileText, X } from 'lucide-react'

function VideoInput({ onSubmit, onUpload, status, message }) {
    const [url, setUrl] = useState('')
    const [uploadMode, setUploadMode] = useState(false)
    const [selectedFile, setSelectedFile] = useState(null)
    const [customTitle, setCustomTitle] = useState('')
    const fileInputRef = useRef(null)

    const handleSubmit = (e) => {
        e.preventDefault()
        if (url.trim() && status !== 'loading') {
            onSubmit(url.trim())
        }
    }

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0]
        if (file) {
            // Validate file type
            const validTypes = ['.srt', '.vtt', '.txt']
            const ext = '.' + file.name.split('.').pop()?.toLowerCase()

            if (!validTypes.includes(ext)) {
                alert('Please upload a .srt, .vtt, or .txt file')
                return
            }

            setSelectedFile(file)
            // Use filename as title suggestion
            setCustomTitle(file.name.replace(/\.[^/.]+$/, ''))
        }
    }

    const handleUpload = (e) => {
        e.preventDefault()
        if (selectedFile && status !== 'loading' && onUpload) {
            onUpload(selectedFile, customTitle)
        }
    }

    const clearFile = () => {
        setSelectedFile(null)
        setCustomTitle('')
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    return (
        <div className="video-input-container">
            {/* Toggle between URL and Upload modes */}
            <div className="input-mode-toggle">
                <button
                    type="button"
                    className={`mode-btn ${!uploadMode ? 'active' : ''}`}
                    onClick={() => setUploadMode(false)}
                >
                    <Search size={16} />
                    YouTube URL
                </button>
                <button
                    type="button"
                    className={`mode-btn ${uploadMode ? 'active' : ''}`}
                    onClick={() => setUploadMode(true)}
                >
                    <Upload size={16} />
                    Upload Transcript
                </button>
            </div>

            {!uploadMode ? (
                /* YouTube URL Input */
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
            ) : (
                /* File Upload Form */
                <form onSubmit={handleUpload} className="upload-form">
                    <div className="upload-area">
                        {!selectedFile ? (
                            <label className="upload-dropzone">
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    accept=".srt,.vtt,.txt"
                                    onChange={handleFileSelect}
                                    disabled={status === 'loading'}
                                    hidden
                                />
                                <Upload size={32} className="upload-icon" />
                                <span className="upload-text">
                                    Click to upload transcript
                                </span>
                                <span className="upload-hint">
                                    Supports: SRT, VTT, TXT
                                </span>
                            </label>
                        ) : (
                            <div className="selected-file">
                                <FileText size={24} className="file-icon" />
                                <div className="file-info">
                                    <span className="file-name">{selectedFile.name}</span>
                                    <span className="file-size">
                                        {(selectedFile.size / 1024).toFixed(1)} KB
                                    </span>
                                </div>
                                <button
                                    type="button"
                                    className="remove-file-btn"
                                    onClick={clearFile}
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        )}
                    </div>

                    {selectedFile && (
                        <>
                            <input
                                type="text"
                                className="video-input title-input"
                                placeholder="Video/Lesson title (optional)"
                                value={customTitle}
                                onChange={(e) => setCustomTitle(e.target.value)}
                                disabled={status === 'loading'}
                            />
                            <button
                                type="submit"
                                className="video-submit-btn upload-btn"
                                disabled={status === 'loading'}
                            >
                                {status === 'loading' ? (
                                    <Loader2 size={20} className="animate-spin" />
                                ) : (
                                    <Upload size={20} />
                                )}
                                <span>Process Transcript</span>
                            </button>
                        </>
                    )}
                </form>
            )}

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
