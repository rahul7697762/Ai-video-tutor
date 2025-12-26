import { useRef, useEffect, useCallback } from 'react'
import ReactPlayer from 'react-player/youtube'

function VideoPlayer({ videoId, onPause, onPlay, onProgress }) {
    const playerRef = useRef(null)
    const lastTimeRef = useRef(0)

    // Handle player state changes
    const handlePause = useCallback(() => {
        if (playerRef.current) {
            const currentTime = playerRef.current.getCurrentTime()
            onPause(currentTime)
        }
    }, [onPause])

    const handlePlay = useCallback(() => {
        onPlay()
    }, [onPlay])

    const handleProgress = useCallback((state) => {
        // Update progress every second
        const currentTime = Math.floor(state.playedSeconds)
        if (currentTime !== lastTimeRef.current) {
            lastTimeRef.current = currentTime
            onProgress(currentTime)
        }
    }, [onProgress])

    // Build YouTube URL
    const videoUrl = `https://www.youtube.com/watch?v=${videoId}`

    return (
        <div className="video-player-container">
            <ReactPlayer
                ref={playerRef}
                url={videoUrl}
                width="100%"
                height="100%"
                playing={false}
                controls={true}
                onPause={handlePause}
                onPlay={handlePlay}
                onProgress={handleProgress}
                progressInterval={500}
                config={{
                    youtube: {
                        playerVars: {
                            modestbranding: 1,
                            rel: 0,
                        },
                    },
                }}
            />
        </div>
    )
}

export default VideoPlayer
