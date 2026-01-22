import React, { useState, useEffect, useRef } from 'react'

function VideoModal({ result, isOpen, onClose, mediaIndex, fpsMapping, onSaveAnswer = null, onDresSubmitClick = null }) {
  const [videoId, setVideoId] = useState(null)
  const [videoFolder, setVideoFolder] = useState(null)
  const [frameIdx, setFrameIdx] = useState(null)
  const [timestamp, setTimestamp] = useState(0)
  const modalBackdropRef = useRef(null)
  const [minutes, setMinutes] = useState(0)
  const [seconds, setSeconds] = useState(0)
  const [calculatedMs, setCalculatedMs] = useState(0)
  
  // YouTube Player API states
  const playerRef = useRef(null)
  const [isYTReady, setIsYTReady] = useState(false)
  const [isPlayerReady, setIsPlayerReady] = useState(false)
  const [autoSync, setAutoSync] = useState(true)
  const autoSyncRef = useRef(true) // Ref to always get latest autoSync value
  const [currentVideoTime, setCurrentVideoTime] = useState(0)
  const playerContainerRef = useRef(null)

  // Update autoSyncRef whenever autoSync changes
  useEffect(() => {
    autoSyncRef.current = autoSync
  }, [autoSync])

  useEffect(() => {
    console.log('[VideoModal] useEffect triggered - isOpen:', isOpen, 'result:', result)
    if (!result || !isOpen) {
      console.log('VideoModal: No result or not open', { result, isOpen })
      return
    }


    const keyframePath = result.keyframe_path
    console.log('VideoModal: keyframe_path =', keyframePath)
    
    if (!keyframePath) {
      console.warn('VideoModal: No keyframe_path in result', result)
      return
    }

    const cleanPath = keyframePath.startsWith('/') ? keyframePath.substring(1) : keyframePath
    const pathParts = cleanPath.split('/')
    console.log('VideoModal: keyframePath =', keyframePath)
    console.log('VideoModal: cleanPath =', cleanPath)
    console.log('VideoModal: pathParts =', pathParts)
    
    if (pathParts.length < 2) {
      console.warn('VideoModal: Invalid keyframe_path format - need at least folder/filename', keyframePath)
      return
    }

    // Extract folder and filename
    // Supports both formats:
    // - 2-level: "keyframes/L01_V001/0.webp" or "L01_V001/0.webp"
    // - 3-level: "keyframes/L02/L02_V001/0.webp" or "L02/L02_V001/0.webp"
    let folder, filename
    
    // Remove 'keyframes' prefix if present
    const startIdx = pathParts[0] === 'keyframes' ? 1 : 0
    const actualParts = pathParts.slice(startIdx)
    
    if (actualParts.length >= 3) {
      // 3-level structure: L02/L02_V001/0.webp
      folder = actualParts[actualParts.length - 2] // e.g., "L02_V001"
      filename = actualParts[actualParts.length - 1] // e.g., "0.webp"
    } else if (actualParts.length >= 2) {
      // 2-level structure: L01_V001/0.webp
      folder = actualParts[0] // e.g., "L01_V001"
      filename = actualParts[1] // e.g., "0.webp"
    } else {
      console.warn('VideoModal: Cannot parse keyframe_path', keyframePath)
      return
    }
    
    const frameIdxValue = parseInt(filename.replace('.webp', ''), 10)

    console.log('VideoModal: folder =', folder, 'frameIdx =', frameIdxValue)
    console.log('VideoModal: mediaIndex loaded?', !!mediaIndex)
    console.log('VideoModal: mediaIndex keys sample:', mediaIndex ? Object.keys(mediaIndex).slice(0, 5) : null)
    console.log('VideoModal: mediaIndex has folder?', mediaIndex ? mediaIndex[folder] !== undefined : false)

    setVideoFolder(folder)
    setFrameIdx(frameIdxValue)

    // Get YouTube video ID from mediaIndex
    if (mediaIndex && mediaIndex[folder]) {
      const youtubeUrl = mediaIndex[folder]
      console.log('VideoModal: YouTube URL =', youtubeUrl)
      
      // Extract video ID from YouTube URL
      // Format: "https://youtube.com/watch?v=VIDEO_ID"
      const match = youtubeUrl.match(/[?&]v=([^&]+)/)
      if (match) {
        const extractedVideoId = match[1]
        console.log('VideoModal: Extracted video ID =', extractedVideoId)
        setVideoId(extractedVideoId)
      } else {
        console.warn('VideoModal: Could not extract video ID from URL', youtubeUrl)
      }
    } else {
      console.warn('VideoModal: Folder not found in mediaIndex', { folder, mediaIndexKeys: mediaIndex ? Object.keys(mediaIndex).slice(0, 5) : null })
    }

    // Calculate timestamp from frame_idx and fps
    if (fpsMapping && fpsMapping[folder] && !isNaN(frameIdxValue)) {
      const fps = fpsMapping[folder]
      const timeInSeconds = frameIdxValue / fps
      setTimestamp(Math.floor(timeInSeconds))
      console.log('VideoModal: Timestamp =', Math.floor(timeInSeconds), 'seconds (FPS:', fps, ')')
    }
  }, [result, isOpen, mediaIndex, fpsMapping])

  // Load YouTube IFrame API
  useEffect(() => {
    if (window.YT && window.YT.Player) {
      setIsYTReady(true)
      return
    }

    const tag = document.createElement('script')
    tag.src = 'https://www.youtube.com/iframe_api'
    const firstScriptTag = document.getElementsByTagName('script')[0]
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag)

    window.onYouTubeIframeAPIReady = () => {
      console.log('[VideoModal] YouTube API Ready')
      setIsYTReady(true)
    }

    return () => {
      window.onYouTubeIframeAPIReady = null
    }
  }, [])

  // Calculate milliseconds when minutes or seconds change
  useEffect(() => {
    // Làm tròn xuống để không có số thập phân
    const totalSeconds = (Number(minutes) || 0) * 60 + (Number(seconds) || 0)
    const ms = Math.floor(totalSeconds * 1000)
    setCalculatedMs(ms)
  }, [minutes, seconds])

  // Initialize YouTube Player
  useEffect(() => {
    if (!isYTReady || !videoId || !isOpen) {
      return
    }

    // Cleanup previous player
    if (playerRef.current) {
      try {
        playerRef.current.destroy()
      } catch (e) {
        console.warn('[VideoModal] Error destroying previous player:', e)
      }
      playerRef.current = null
      setIsPlayerReady(false)
    }

    // Sync time from YouTube player - Define inside useEffect to capture latest state setters
    const syncTimeFromVideo = () => {
      if (!playerRef.current) {
        console.warn('[VideoModal] Player not ready for sync')
        return
      }

      try {
        const currentTime = playerRef.current.getCurrentTime()
        setCurrentVideoTime(currentTime)
        
        const mins = Math.floor(currentTime / 60)
        const secs = currentTime % 60
        
        setMinutes(mins)
        setSeconds(secs)
        
        console.log('[VideoModal] Synced time:', { currentTime, mins, secs })
      } catch (error) {
        console.error('[VideoModal] Error syncing time:', error)
      }
    }

    // Small delay to ensure DOM is ready
    const timer = setTimeout(() => {
      try {
        console.log('[VideoModal] Initializing YouTube Player:', videoId, 'autoSync:', autoSyncRef.current)
        
        playerRef.current = new window.YT.Player(`youtube-player-${videoId}`, {
          videoId: videoId,
          playerVars: {
            start: timestamp,
            autoplay: 1,
            rel: 0,
            modestbranding: 1
          },
          events: {
            onReady: (event) => {
              console.log('[VideoModal] Player ready')
              setIsPlayerReady(true)
            },
            onStateChange: (event) => {
              console.log('[VideoModal] State change:', event.data, 'autoSync:', autoSyncRef.current)
              // YT.PlayerState.PAUSED = 2
              if (event.data === 2 && autoSyncRef.current) {
                console.log('[VideoModal] Video paused, auto-syncing...')
                setTimeout(() => syncTimeFromVideo(), 100) // Small delay to ensure state is ready
              }
            }
          }
        })
      } catch (error) {
        console.error('[VideoModal] Error initializing player:', error)
      }
    }, 100)

    return () => {
      clearTimeout(timer)
      if (playerRef.current) {
        try {
          playerRef.current.destroy()
        } catch (e) {
          console.warn('[VideoModal] Error destroying player on cleanup:', e)
        }
        playerRef.current = null
      }
      setIsPlayerReady(false)
    }
  }, [isYTReady, videoId, isOpen, timestamp])

  // Sync time from YouTube player - Public function for manual sync button
  const syncTimeFromVideo = () => {
    if (!playerRef.current || !isPlayerReady) {
      console.warn('[VideoModal] Player not ready for sync')
      return
    }

    try {
      const currentTime = playerRef.current.getCurrentTime()
      setCurrentVideoTime(currentTime)
      
      const mins = Math.floor(currentTime / 60)
      const secs = currentTime % 60
      
      setMinutes(mins)
      setSeconds(secs)
      
      console.log('[VideoModal] Synced time:', { currentTime, mins, secs })
    } catch (error) {
      console.error('[VideoModal] Error syncing time:', error)
    }
  }

  // Prevent background scrolling when modal is open
  useEffect(() => {
    if (isOpen) {
      // Save original overflow to restore later
      const originalOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = originalOverflow || ''
      }
    }
    return undefined
  }, [isOpen])

  if (!isOpen || !result) return null

  // Build YouTube embed URL with timestamp and autoplay
  const youtubeEmbedUrl = videoId
    ? `https://www.youtube-nocookie.com/embed/${videoId}?start=${timestamp}&autoplay=1&rel=0`
    : null

  console.log('[VideoModal] ===== DEBUG INFO =====')
  console.log('[VideoModal] videoId:', videoId)
  console.log('[VideoModal] timestamp:', timestamp)
  console.log('[VideoModal] youtubeEmbedUrl:', youtubeEmbedUrl)
  console.log('[VideoModal] result:', result)
  console.log('[VideoModal] ========================')

  return (
    <div
      ref={modalBackdropRef}
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
      style={{
        // Position relative to main content area
        left: 0,
        top: 0,
        right: 0,
        bottom: 0,
      }}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-3 sm:p-4 border-b">
          <h2 className="text-lg sm:text-xl font-semibold text-gray-800">Video Details</h2>
          <div className="flex items-center gap-2">
            {onSaveAnswer && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (onSaveAnswer) {
                    onSaveAnswer(result)
                    onClose()
                  }
                }}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center gap-2"
                title="Save as Answer"
              >
                <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
                <span>Save as Answer</span>
              </button>
            )}
            {onDresSubmitClick && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDresSubmitClick(result)
                }}
                className="px-3 py-1.5 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 flex items-center gap-2"
                title="Submit to DRES"
              >
                <svg
                  className="h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span>Submit DRES</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 text-xl sm:text-2xl font-bold leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content - Layout mới với video bên trái và tool panel bên phải */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-4 md:p-6">
          {/* Metadata - Compact */}
          <div className="mb-3 sm:mb-4">
            <div className="text-xs sm:text-sm text-gray-600 flex flex-wrap gap-x-3 sm:gap-x-4 gap-y-1">
              <span><span className="font-medium">Folder:</span> {videoFolder || 'N/A'}</span>
              <span><span className="font-medium">Frame:</span> {frameIdx !== null ? frameIdx : 'N/A'}</span>
              {fpsMapping && videoFolder && fpsMapping[videoFolder] && (
                <span><span className="font-medium">FPS:</span> {fpsMapping[videoFolder]}</span>
              )}
              <span>
                <span className="font-medium">Time:</span>{' '}
                {timestamp > 0
                  ? `${Math.floor(timestamp / 60)}:${String(timestamp % 60).padStart(2, '0')}`
                  : '0:00'}
              </span>
            </div>
          </div>

          {/* Video Player và Tool Panel - Layout ngang */}
          <div className="flex gap-4">
            {/* Video Player - Bên trái */}
            <div className="flex-1">
              {videoId ? (
                <div className="relative w-full pb-[56.25%] bg-gray-100 rounded-lg overflow-hidden">
                  <div
                    id={`youtube-player-${videoId}`}
                    ref={playerContainerRef}
                    className="absolute top-0 left-0 w-full h-full"
                  ></div>
                </div>
              ) : (
                <div className="relative w-full pb-[56.25%] bg-gray-100 rounded-lg flex items-center justify-center">
                  <p className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm sm:text-base">
                    Video not available
                  </p>
                </div>
              )}
            </div>

            {/* Time Calculator Tool Panel - Bên phải */}
            <div className="w-80 flex-shrink-0">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-800">
                    Time Calculator
                  </h3>
                  <button
                    onClick={syncTimeFromVideo}
                    disabled={!isPlayerReady}
                    className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    title="Sync current video time"
                  >
                    <svg className="h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Sync Now
                  </button>
                </div>

                {/* Auto Sync Toggle */}
                <div className="flex items-center justify-between py-2 px-3 bg-white rounded-md border border-gray-200">
                  <label className="text-sm font-medium text-gray-700 cursor-pointer" htmlFor="auto-sync-toggle">
                    Auto Sync on Pause
                  </label>
                  <button
                    id="auto-sync-toggle"
                    type="button"
                    onClick={() => setAutoSync(!autoSync)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                      autoSync ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        autoSync ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                {/* Current Video Time Display */}
                {isPlayerReady && (
                  <div className="py-2 px-3 bg-blue-50 rounded-md border border-blue-200">
                    <div className="text-xs font-medium text-blue-700 mb-1">Current Video Time</div>
                    <div className="text-sm font-mono font-semibold text-blue-900">
                      {Math.floor(currentVideoTime / 60)}:{String(Math.floor(currentVideoTime % 60)).padStart(2, '0')}
                      {currentVideoTime > 0 && (
                        <span className="text-xs text-blue-600 ml-1">
                          ({Math.floor(currentVideoTime * 1000).toLocaleString()} ms)
                        </span>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Input fields */}
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Phút
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={minutes}
                      onChange={(e) => setMinutes(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="0"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Giây
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.001" // Cho phép nhập số thập phân
                      value={seconds}
                      onChange={(e) => {
                        const val = Number(e.target.value) || 0
                        if (val >= 0) {
                          setSeconds(val) // Không giới hạn max 59, cho phép số thập phân
                        }
                      }}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                      placeholder="0"
                    />
                  </div>
                </div>

                {/* Result display */}
                <div className="pt-3 border-t border-gray-300">
                  <div className="space-y-2">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Tổng thời gian
                      </label>
                      <div className="text-lg font-mono font-semibold text-gray-800">
                        {String(Math.floor(calculatedMs / 60000)).padStart(2, '0')}:
                        {String(Math.floor((calculatedMs % 60000) / 1000)).padStart(2, '0')}
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Milliseconds (ms)
                      </label>
                      <div className="text-lg font-mono font-semibold text-purple-600 bg-purple-50 px-3 py-2 rounded border border-purple-200">
                        {calculatedMs.toLocaleString('en-US', { maximumFractionDigits: 0 })} {/* Hiển thị không có số thập phân nhưng giá trị không bị làm tròn */}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Submit button */}
                {onDresSubmitClick && videoFolder && (
                  <div className="pt-3">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        // Tạo result object với timeMs đã tính
                        const customResult = {
                          ...result,
                          calculated_time_ms: calculatedMs,
                          video_folder: videoFolder
                        }
                        // Mở DRES modal với custom data
                        onDresSubmitClick(customResult)
                      }}
                      disabled={calculatedMs === 0}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      title="Submit với thời gian đã tính"
                    >
                      <svg
                        className="h-4 w-4"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span>Submit DRES với thời gian này</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VideoModal

