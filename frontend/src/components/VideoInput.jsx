import { useState, useRef } from 'react'
import { Search, Loader2, Upload, FileText, Video, X } from 'lucide-react'

function VideoInput({ onSubmit, onUpload, onVideoUpload, status, message }) {
    const [url, setUrl] = useState('')
    const [uploadMode, setUploadMode] = useState('url') // 'url', 'transcript', 'video'
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
            const ext = '.' + file.name.split('.').pop()?.toLowerCase()

            if (uploadMode === 'transcript') {
                const validTypes = ['.srt', '.vtt', '.txt']
                if (!validTypes.includes(ext)) {
                    alert('Please upload a .srt, .vtt, or .txt file')
                    return
                }
            } else if (uploadMode === 'video') {
                const validTypes = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.mp3', '.wav', '.m4a']
                if (!validTypes.includes(ext)) {
                    alert('Please upload a video or audio file (MP4, MOV, MP3, etc.)')
                    return
                }

                // Check file size (100MB limit)
                if (file.size > 100 * 1024 * 1024) {
                    alert('File too large. Maximum size is 100MB.')
                    return
                }
            }

            setSelectedFile(file)
            setCustomTitle(file.name.replace(/\.[^/.]+$/, ''))
        }
    }

    const handleUpload = (e) => {
        e.preventDefault()
        if (!selectedFile || status === 'loading') return

        if (uploadMode === 'transcript' && onUpload) {
            onUpload(selectedFile, customTitle)
        } else if (uploadMode === 'video' && onVideoUpload) {
            onVideoUpload(selectedFile, customTitle)
        }
    }

    const clearFile = () => {
        setSelectedFile(null)
        setCustomTitle('')
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const getAcceptTypes = () => {
        if (uploadMode === 'transcript') {
            return '.srt,.vtt,.txt'
        }
        return '.mp4,.mov,.avi,.mkv,.webm,.m4v,.mp3,.wav,.m4a'
    }

    const getUploadHint = () => {
        if (uploadMode === 'transcript') {
            return 'Supports: SRT, VTT, TXT'
        }
        return 'Supports: MP4, MOV, MP3, WAV (max 100MB)'
    }

    const getUploadText = () => {
        if (uploadMode === 'transcript') {
            return 'Click to upload transcript'
        }
        return 'Click to upload video/audio'
    }

    const getButtonText = () => {
        if (uploadMode === 'transcript') {
            return 'Process Transcript'
        }
        return 'Transcribe & Process'
    }

    return (
        <div className="video-input-container">
            {/* Toggle between URL, Transcript, and Video modes */}
            <div className="input-mode-toggle">
                <button
                    type="button"
                    className={`mode-btn ${uploadMode === 'url' ? 'active' : ''}`}
                    onClick={() => { setUploadMode('url'); clearFile() }}
                >
                    <Search size={16} />
                    YouTube URL
                </button>
                <button
                    type="button"
                    className={`mode-btn ${uploadMode === 'transcript' ? 'active' : ''}`}
                    onClick={() => { setUploadMode('transcript'); clearFile() }}
                >
                    <FileText size={16} />
                    Transcript
                </button>
                <button
                    type="button"
                    className={`mode-btn ${uploadMode === 'video' ? 'active' : ''}`}
                    onClick={() => { setUploadMode('video'); clearFile() }}
                >
                    <Video size={16} />
                    Video/Audio
                </button>
            </div>

            {uploadMode === 'url' ? (
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
                                    accept={getAcceptTypes()}
                                    onChange={handleFileSelect}
                                    disabled={status === 'loading'}
                                    hidden
                                />
                                {uploadMode === 'video' ? (
                                    <Video size={32} className="upload-icon" />
                                ) : (
                                    <Upload size={32} className="upload-icon" />
                                )}
                                <span className="upload-text">
                                    {getUploadText()}
                                </span>
                                <span className="upload-hint">
                                    {getUploadHint()}
                                </span>
                            </label>
                        ) : (
                            <div className="selected-file">
                                {uploadMode === 'video' ? (
                                    <Video size={24} className="file-icon" />
                                ) : (
                                    <FileText size={24} className="file-icon" />
                                )}
                                <div className="file-info">
                                    <span className="file-name">{selectedFile.name}</span>
                                    <span className="file-size">
                                        {selectedFile.size > 1024 * 1024
                                            ? `${(selectedFile.size / 1024 / 1024).toFixed(1)} MB`
                                            : `${(selectedFile.size / 1024).toFixed(1)} KB`
                                        }
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
                                <span>{getButtonText()}</span>
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
