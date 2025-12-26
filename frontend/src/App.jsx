import { useState, useCallback } from 'react'
import Header from './components/Header'
import VideoInput from './components/VideoInput'
import VideoPlayer from './components/VideoPlayer'
import ExplanationPanel from './components/ExplanationPanel'
import LearningHistory from './components/LearningHistory'
import './App.css'

// API base URL - uses VITE_API_URL in production, empty for dev (uses Vite proxy)
const API_BASE = import.meta.env.VITE_API_URL || ''

function App() {
  // Video state
  const [videoId, setVideoId] = useState('')
  const [videoReady, setVideoReady] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  // Ingestion state
  const [ingestionStatus, setIngestionStatus] = useState('idle') // idle, loading, ready, error
  const [ingestionMessage, setIngestionMessage] = useState('')

  // Explanation state
  const [explanation, setExplanation] = useState(null)
  const [isExplaining, setIsExplaining] = useState(false)
  const [explanationError, setExplanationError] = useState('')

  // History state
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  // Handle video URL submission
  const handleVideoSubmit = useCallback(async (url) => {
    // Extract video ID from URL
    const extractedId = extractVideoId(url)

    if (!extractedId) {
      setIngestionStatus('error')
      setIngestionMessage('Invalid YouTube URL. Please enter a valid video link.')
      return
    }

    setVideoId(extractedId)
    setVideoReady(false)
    setIngestionStatus('loading')
    setIngestionMessage('Extracting transcript and building knowledge base...')
    setExplanation(null)

    try {
      // Call ingestion API
      const response = await fetch(`${API_BASE}/api/transcript/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: extractedId }),
      })

      const data = await response.json()

      if (data.status === 'exists' || data.status === 'ready') {
        setIngestionStatus('ready')
        setIngestionMessage('Ready! Pause the video anytime to get an explanation.')
        setVideoReady(true)
      } else if (data.status === 'queued' || data.status === 'processing') {
        // Poll for completion
        pollIngestionStatus(extractedId)
      } else {
        setIngestionStatus('error')
        setIngestionMessage(data.message || 'Failed to process video')
      }
    } catch (error) {
      console.error('Ingestion error:', error)
      setIngestionStatus('error')
      setIngestionMessage('Could not connect to server. Make sure the backend is running.')
    }
  }, [])

  // Handle transcript file upload
  const handleUpload = useCallback(async (file, title) => {
    setVideoReady(false)
    setIngestionStatus('loading')
    setIngestionMessage('Uploading and processing transcript...')
    setExplanation(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (title) {
        formData.append('video_title', title)
      }

      const response = await fetch(`${API_BASE}/api/transcript/upload`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        setIngestionStatus('error')
        setIngestionMessage(data.detail || 'Failed to upload transcript')
        return
      }

      // Set the video ID from response
      setVideoId(data.video_id)

      if (data.status === 'queued' || data.status === 'processing') {
        // Poll for completion
        pollIngestionStatus(data.video_id)
      } else if (data.status === 'ready') {
        setIngestionStatus('ready')
        setIngestionMessage('Transcript processed! Ready for explanations.')
        setVideoReady(true)
      } else {
        setIngestionStatus('error')
        setIngestionMessage(data.message || 'Failed to process transcript')
      }
    } catch (error) {
      console.error('Upload error:', error)
      setIngestionStatus('error')
      setIngestionMessage('Could not connect to server. Make sure the backend is running.')
    }
  }, [])

  // Poll for ingestion status
  const pollIngestionStatus = useCallback(async (id) => {
    let attempts = 0
    const maxAttempts = 60 // 60 * 2s = 2 minutes max

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/transcript/status/${id}`)
        const data = await response.json()

        if (data.status === 'ready') {
          setIngestionStatus('ready')
          setIngestionMessage(`Ready! ${data.total_chunks || ''} sections indexed.`)
          setVideoReady(true)
          return
        } else if (data.status === 'error') {
          setIngestionStatus('error')
          setIngestionMessage('Failed to process video transcript.')
          return
        }

        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000)
        } else {
          setIngestionStatus('error')
          setIngestionMessage('Processing timed out. Please try again.')
        }
      } catch (error) {
        setIngestionStatus('error')
        setIngestionMessage('Connection error while checking status.')
      }
    }

    poll()
  }, [])

  // Handle pause - trigger explanation
  const handlePause = useCallback(async (time) => {
    if (!videoReady || !videoId) return

    setIsPlaying(false)
    setCurrentTime(time)

    // Auto-trigger explanation on pause
    requestExplanation(time)
  }, [videoReady, videoId])

  // Request explanation for current timestamp
  const requestExplanation = useCallback(async (timestamp, query = null) => {
    if (!videoId || isExplaining) return

    setIsExplaining(true)
    setExplanationError('')
    setExplanation(null)

    try {
      const response = await fetch(`${API_BASE}/api/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: videoId,
          timestamp: timestamp,
          user_query: query || "I don't understand this",
          include_audio: true,
          max_chunks: 8,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to generate explanation')
      }

      const data = await response.json()

      // Format audio URL
      if (data.audio_url) {
        data.audio_url = `${API_BASE}${data.audio_url}`
      }

      setExplanation(data)

      // Add to history
      setHistory(prev => [{
        id: Date.now(),
        videoId,
        timestamp,
        topic: data.primary_topic,
        summary: data.summary,
        createdAt: new Date(),
      }, ...prev.slice(0, 19)]) // Keep last 20

    } catch (error) {
      console.error('Explanation error:', error)
      setExplanationError(error.message || 'Failed to generate explanation')
    } finally {
      setIsExplaining(false)
    }
  }, [videoId, isExplaining])

  // Handle play
  const handlePlay = useCallback(() => {
    setIsPlaying(true)
  }, [])

  // Handle progress update
  const handleProgress = useCallback((time) => {
    setCurrentTime(time)
  }, [])

  return (
    <div className="app">
      <Header
        onHistoryClick={() => setShowHistory(!showHistory)}
        historyCount={history.length}
      />

      <main className="main-content">
        {!videoId ? (
          // Landing / Video Input View
          <div className="landing-view animate-fadeIn">
            <div className="hero-section">
              <div className="hero-badge">
                <span className="badge-icon">✨</span>
                AI-Powered Learning
              </div>
              <h1 className="hero-title">
                Never Get <span className="gradient-text">Confused</span> by a YouTube Video Again
              </h1>
              <p className="hero-subtitle">
                Just paste a video link, hit play, and pause whenever you don't understand something.
                Our AI tutor explains concepts in simple terms—like having a patient teacher by your side.
              </p>
            </div>

            <VideoInput
              onSubmit={handleVideoSubmit}
              onUpload={handleUpload}
              status={ingestionStatus}
              message={ingestionMessage}
            />

            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon">🎯</div>
                <h3>Zero Prior Knowledge</h3>
                <p>Every explanation assumes you're a complete beginner. No jargon, just clarity.</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🧠</div>
                <h3>Smart Context</h3>
                <p>AI understands the video's teaching flow and builds on earlier concepts.</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔊</div>
                <h3>Listen or Read</h3>
                <p>Get explanations as text or natural audio—whatever works best for you.</p>
              </div>
            </div>
          </div>
        ) : (
          // Video Learning View
          <div className="learning-view">
            <div className="video-section">
              <VideoPlayer
                videoId={videoId}
                onPause={handlePause}
                onPlay={handlePlay}
                onProgress={handleProgress}
              />

              {ingestionStatus === 'loading' && (
                <div className="ingestion-overlay">
                  <div className="ingestion-spinner"></div>
                  <p>{ingestionMessage}</p>
                </div>
              )}

              {videoReady && !isPlaying && (
                <div className="pause-hint animate-fadeIn">
                  <span className="hint-icon">💡</span>
                  Video paused at {formatTime(currentTime)} — Explanation ready!
                </div>
              )}
            </div>

            <ExplanationPanel
              explanation={explanation}
              isLoading={isExplaining}
              error={explanationError}
              timestamp={currentTime}
              onAskFollowup={(query) => requestExplanation(currentTime, query)}
            />
          </div>
        )}
      </main>

      {showHistory && (
        <LearningHistory
          history={history}
          onClose={() => setShowHistory(false)}
          onSelectEntry={(entry) => {
            setVideoId(entry.videoId)
            // Could also seek to timestamp
          }}
        />
      )}
    </div>
  )
}

// Utility: Extract YouTube video ID
function extractVideoId(url) {
  if (!url) return null

  // Already a video ID (11 chars)
  if (/^[a-zA-Z0-9_-]{11}$/.test(url)) {
    return url
  }

  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/,
  ]

  for (const pattern of patterns) {
    const match = url.match(pattern)
    if (match) return match[1]
  }

  return null
}

// Utility: Format time as MM:SS
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export default App
