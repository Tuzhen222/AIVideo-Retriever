import React, { useState, useEffect, useRef } from 'react'

function VideoModal({ result, isOpen, onClose, mediaIndex, fpsMapping, onSaveAnswer = null, onDresSubmitClick = null }) {
  const [videoId, setVideoId] = useState(null)
  const [videoFolder, setVideoFolder] = useState(null)
  const [frameIdx, setFrameIdx] = useState(null)
  const [timestamp, setTimestamp] = useState(0)
  const modalBackdropRef = useRef(null)

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
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
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

        {/* Content */}
        <div className="p-3 sm:p-4 md:p-6">
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

          {/* Video Player */}
          <div>
            {youtubeEmbedUrl ? (
              <div className="relative w-full pb-[56.25%] bg-gray-100 rounded-lg overflow-hidden">
                <iframe
                  src={youtubeEmbedUrl}
                  title="YouTube video player"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  className="absolute top-0 left-0 w-full h-full"
                ></iframe>
              </div>
            ) : (
              <div className="relative w-full pb-[56.25%] bg-gray-100 rounded-lg flex items-center justify-center">
                <p className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm sm:text-base">
                  Video not available
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default VideoModal

