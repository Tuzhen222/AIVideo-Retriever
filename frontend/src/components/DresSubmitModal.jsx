import React, { useEffect, useState } from 'react'
import Toast from './Toast'

const DEFAULT_OFFSET_MS = 50
const DEFAULT_DRES_BASE_URL = 'http://192.168.20.156:5601/api/v2'

function extractFromKeyframePath(keyframePath, fpsMapping = null) {
  if (!keyframePath) {
    return { videoId: '', timeMs: '', frameIndex: '', videoFolder: '' }
  }

  const parts = keyframePath.split('/').filter(Boolean)
  let folder, filename
  
  // Remove 'keyframes' prefix if present
  const startIdx = parts[0] === 'keyframes' ? 1 : 0
  const actualParts = parts.slice(startIdx)
  
  // Handle both 2-level and 3-level structures:
  // - 2-level: "L01_V001/0.webp"
  // - 3-level: "L02/L02_V001/0.webp"
  if (actualParts.length >= 3) {
    // 3-level structure: L02/L02_V001/0.webp
    folder = actualParts[actualParts.length - 2] // e.g., "L02_V001"
    filename = actualParts[actualParts.length - 1] // e.g., "0.webp"
  } else if (actualParts.length >= 2) {
    // 2-level structure: L01_V001/0.webp
    folder = actualParts[0] // e.g., "L01_V001"
    filename = actualParts[1] // e.g., "0.webp"
  } else {
    return { videoId: '', timeMs: '', frameIndex: '', videoFolder: '' }
  }

  const numMatch = filename.match(/(\d+)/)
  const frameIndex = numMatch ? parseInt(numMatch[1], 10) : ''
  
  // Convert frame index to milliseconds using FPS
  let timeMs = ''
  if (Number.isFinite(frameIndex) && fpsMapping && fpsMapping[folder]) {
    const fps = fpsMapping[folder]
    const timeInSeconds = frameIndex / fps
    timeMs = Math.round(timeInSeconds * 1000) // Convert to milliseconds
  } else if (Number.isFinite(frameIndex)) {
    // Fallback: if no FPS mapping, use frame index as-is (for backward compatibility)
    timeMs = frameIndex
  }

  return {
    videoId: folder.replace(/\.[^/.]+$/, ''),
    timeMs: timeMs,
    frameIndex: frameIndex,
    videoFolder: folder
  }
}

function DresSubmitModal({ isOpen, onClose, initialData, fpsMapping = null, tupleData = null }) {
  const [mode, setMode] = useState('KIS') // 'KIS', 'QA', or 'TRAKE'
  const [sessionId, setSessionId] = useState('')
  const [evaluationId, setEvaluationId] = useState('')
  const [answer, setAnswer] = useState('')
  const [videoId, setVideoId] = useState('')
  const [timeMs, setTimeMs] = useState('')
  const [startMs, setStartMs] = useState('')
  const [endMs, setEndMs] = useState('')
  const [frameIds, setFrameIds] = useState('') // Comma-separated frame IDs for TRAKE
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [toast, setToast] = useState({ isVisible: false, message: null, type: 'info' })
  const [isLoadingSession, setIsLoadingSession] = useState(false)
  const [isLoadingEvaluation, setIsLoadingEvaluation] = useState(false)
  const [dresBaseUrl, setDresBaseUrl] = useState(DEFAULT_DRES_BASE_URL)

  // Load persisted values
  useEffect(() => {
    if (!isOpen) return

    const storedSession = window.localStorage.getItem('dres_session_id') || ''
    const storedEval = window.localStorage.getItem('dres_evaluation_id') || ''
    const storedMode = window.localStorage.getItem('dres_mode') || 'KIS'
    const storedBaseUrl = window.localStorage.getItem('dres_base_url') || DEFAULT_DRES_BASE_URL

    setSessionId(storedSession)
    setEvaluationId(storedEval)
    setMode(['KIS', 'QA', 'TRAKE'].includes(storedMode) ? storedMode : 'KIS')
    setDresBaseUrl(storedBaseUrl)

    if (initialData) {
      const { keyframe_path, query_text, calculated_time_ms, video_folder } = initialData
      const { videoId: vf, timeMs: tf, frameIndex: frameIdx } = extractFromKeyframePath(keyframe_path, fpsMapping)

      // Ưu tiên video_folder nếu có (từ time calculator)
      setVideoId(video_folder || vf || '')
      
      // Nếu có calculated_time_ms, dùng nó thay vì timeMs từ keyframe
      if (calculated_time_ms !== null && calculated_time_ms !== undefined) {
        const roundedMs = Math.floor(Number(calculated_time_ms))
        setTimeMs(roundedMs)
        // KIS: start = end = calculated_time_ms (làm tròn)
        setStartMs(roundedMs)
        setEndMs(roundedMs)
      } else {
        setTimeMs(tf || '')
        // KIS: start = end = timeMs (no offset)
        if (Number.isFinite(tf)) {
          setStartMs(Math.floor(tf))
          setEndMs(Math.floor(tf))
        } else {
          setStartMs('')
          setEndMs('')
        }
      }

      setAnswer(query_text || '')
      
      // For TRAKE, prefill with single frame ID if available (keep as frame index, not ms)
      if (Number.isFinite(frameIdx)) {
        setFrameIds(String(frameIdx))
      } else {
        setFrameIds('')
      }
    }

    // Handle tuple data (for TRAKE mode - fill all frame_indices from tuple)
    if (tupleData && tupleData.frame_indices && Array.isArray(tupleData.frame_indices)) {
      setVideoId(tupleData.video || '')
      setMode('TRAKE')
      // Fill all frame indices from tuple, comma-separated
      const frameIdsStr = tupleData.frame_indices.map(idx => String(idx)).join(',')
      setFrameIds(frameIdsStr)
    }

    setError('')
    setSuccess('')
  }, [isOpen, initialData, tupleData])

  const handleModeChange = (newMode) => {
    setMode(newMode)
    window.localStorage.setItem('dres_mode', newMode)
  }

  const handleLogin = async () => {
    const username = prompt('Nhập username:')
    if (!username) return

    const password = prompt('Nhập password:')
    if (!password) return

    setIsLoadingSession(true)
    setError('')
    try {
      const resp = await fetch(`${dresBaseUrl}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      })

      const data = await resp.json()
      
      if (!resp.ok) {
        throw new Error(data.message || `HTTP ${resp.status}`)
      }

      if (data.sessionId) {
        setSessionId(data.sessionId)
        window.localStorage.setItem('dres_session_id', data.sessionId)
        
        // Tự động set evaluationId nếu có trong response
        if (data.evaluationId) {
          setEvaluationId(data.evaluationId)
          window.localStorage.setItem('dres_evaluation_id', data.evaluationId)
          setSuccess('Đã lấy Session ID và Evaluation ID thành công!')
        } else {
          setSuccess('Đã lấy Session ID thành công!')
        }
        
        setToast({
          isVisible: true,
          message: data,
          type: 'success'
        })
      } else {
        throw new Error('Không tìm thấy sessionId trong response')
      }
    } catch (err) {
      console.error('Login failed:', err)
      setError(`Lỗi đăng nhập: ${err.message}`)
      setToast({
        isVisible: true,
        message: { error: err.message },
        type: 'error'
      })
    } finally {
      setIsLoadingSession(false)
    }
  }

  const handleGetEvaluations = async () => {
    if (!sessionId.trim()) {
      setError('Vui lòng lấy Session ID trước')
      return
    }

    setIsLoadingEvaluation(true)
    setError('')
    try {
      const url = `${dresBaseUrl}/client/evaluation/list?session=${encodeURIComponent(sessionId.trim())}`
      const resp = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      const data = await resp.json()
      
      if (!resp.ok) {
        throw new Error(data.message || `HTTP ${resp.status}`)
      }

      if (Array.isArray(data) && data.length > 0) {
        // Hiển thị danh sách để chọn
        const evalList = data.map((e, i) => `${i + 1}. ${e.name} (${e.id})`).join('\n')
        const choice = prompt(`Chọn evaluation (nhập số):\n\n${evalList}\n\nNhập số thứ tự:`)
        
        if (choice) {
          const index = parseInt(choice) - 1
          if (index >= 0 && index < data.length) {
            const selected = data[index]
            setEvaluationId(selected.id)
            window.localStorage.setItem('dres_evaluation_id', selected.id)
            setSuccess(`Đã chọn evaluation: ${selected.name}`)
            setToast({
              isVisible: true,
              message: selected,
              type: 'success'
            })
          } else {
            setError('Số thứ tự không hợp lệ')
          }
        }
      } else {
        throw new Error('Không tìm thấy evaluation nào')
      }
    } catch (err) {
      console.error('Get evaluations failed:', err)
      setError(`Lỗi lấy evaluations: ${err.message}`)
      setToast({
        isVisible: true,
        message: { error: err.message },
        type: 'error'
      })
    } finally {
      setIsLoadingEvaluation(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!sessionId.trim() || !evaluationId.trim()) {
      setError('Vui lòng nhập đầy đủ Session ID và Evaluation ID')
      return
    }

    if (!videoId.trim()) {
      setError('Vui lòng nhập Video ID')
      return
    }

    const url = `${dresBaseUrl}/submit/${encodeURIComponent(
      evaluationId.trim()
    )}?session=${encodeURIComponent(sessionId.trim())}`

    let body
    if (mode === 'QA') {
      const finalTimeMs = Math.floor(Number(timeMs))
      if (!Number.isFinite(finalTimeMs)) {
        setError('TIME (ms) không hợp lệ cho chế độ QA')
        return
      }

      if (!answer.trim()) {
        setError('Vui lòng nhập ANSWER cho chế độ QA')
        return
      }

      // Format: QA-<ANSWER>-<VIDEO_ID>-<TIME(ms)>
      const answerQa = `QA-${answer.trim()}-${videoId.trim()}-${finalTimeMs}`
      body = {
        answerSets: [
          {
            answers: [
              {
                text: answerQa
              }
            ]
          }
        ]
      }
    } else if (mode === 'TRAKE') {
      if (!frameIds.trim()) {
        setError('Vui lòng nhập danh sách Frame IDs cho chế độ TRAKE')
        return
      }

      if (!videoId.trim()) {
        setError('Vui lòng nhập Video ID cho chế độ TRAKE')
        return
      }

      // Parse comma-separated frame IDs and validate
      const frameIdParts = frameIds.split(',').map((id) => id.trim()).filter((id) => id.length > 0)
      
      if (frameIdParts.length === 0) {
        setError('Vui lòng nhập ít nhất một Frame ID hợp lệ')
        return
      }

      // Validate frame IDs are numbers (TRAKE uses Frame IDs directly, not milliseconds)
      for (const id of frameIdParts) {
        const num = Number(id)
        if (!Number.isFinite(num)) {
          setError(`Frame ID không hợp lệ: ${id}`)
          return
        }
      }

      // Format: TR-<VIDEO_ID>-<FRAME_ID1>,<FRAME_ID2>,... (Frame IDs, not milliseconds)
      const trakeText = `TR-${videoId.trim()}-${frameIdParts.join(',')}`
      body = {
        answerSets: [
          {
            answers: [
              {
                text: trakeText
              }
            ]
          }
        ]
      }
    } else {
      // KIS mode
      const s = Math.floor(Number(startMs))
      const eMs = Math.floor(Number(endMs))

      if (!Number.isFinite(s) || !Number.isFinite(eMs)) {
        setError('Start / End (ms) không hợp lệ cho chế độ KIS')
        return
      }

      body = {
        answerSets: [
          {
            answers: [
              {
                mediaItemName: videoId.trim(),
                start: s,
                end: eMs
              }
            ]
          }
        ]
      }
    }

    // Persist IDs for next time
    window.localStorage.setItem('dres_session_id', sessionId.trim())
    window.localStorage.setItem('dres_evaluation_id', evaluationId.trim())

    setIsSubmitting(true)
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      // Parse response (có thể là JSON hoặc text)
      let responseData
      const contentType = resp.headers.get('content-type')
      
      try {
        if (contentType && contentType.includes('application/json')) {
          responseData = await resp.json()
        } else {
          const text = await resp.text()
          // Try to parse as JSON, fallback to text
          try {
            responseData = JSON.parse(text)
          } catch {
            responseData = { message: text, status: resp.status }
          }
        }
      } catch (parseErr) {
        responseData = { error: 'Không thể parse response', status: resp.status }
      }

      if (!resp.ok) {
        // Lỗi từ server
        const errorMsg = typeof responseData === 'string' 
          ? responseData 
          : (responseData.message || responseData.error || `HTTP ${resp.status}`)
        setError(errorMsg)
        setToast({
          isVisible: true,
          message: responseData,
          type: 'error'
        })
        return
      }

      // Thành công - giữ lại sessionId và evaluationId để nộp tiếp
      setSuccess('Nộp bài thành công lên DRES!')
      // sessionId và evaluationId đã được lưu vào localStorage ở dòng 361-362
      // Không reset chúng để có thể nộp tiếp đáp án khác
      setToast({
        isVisible: true,
        message: responseData,
        type: 'success'
      })
    } catch (err) {
      console.error('DRES submit failed:', err)
      const errorMsg = err.message || 'Unknown error'
      setError(`Lỗi khi nộp bài: ${errorMsg}`)
      setToast({
        isVisible: true,
        message: { error: errorMsg, type: 'network_error' },
        type: 'error'
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) return null

  const answerQaPreview =
    mode === 'QA' && videoId && timeMs && answer
      ? `QA-${answer}-${videoId}-${timeMs}`
      : ''

  const trakePreview =
    mode === 'TRAKE' && videoId && frameIds.trim()
      ? `TR-${videoId}-${frameIds
          .split(',')
          .map((id) => id.trim())
          .filter((id) => id.length > 0)
          .join(',')}`
      : ''

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
        <div className="bg-white rounded-lg shadow-xl w-full max-w-xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <h2 className="text-lg font-semibold text-gray-800">
            Submit to DRES
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* DRES Base URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              DRES Base URL
            </label>
            <input
              type="text"
              value={dresBaseUrl}
              onChange={(e) => {
                const newUrl = e.target.value
                setDresBaseUrl(newUrl)
                window.localStorage.setItem('dres_base_url', newUrl)
              }}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="http://192.168.20.156:5601/api/v2"
            />
          </div>

          {/* Session & Evaluation ID */}
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Session ID
              </label>
              <input
                type="text"
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Nhập sessionId..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Evaluation ID
              </label>
              <input
                type="text"
                value={evaluationId}
                onChange={(e) => setEvaluationId(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Nhập evaluationId..."
              />
              <p className="mt-1 text-xs text-gray-500">
                URL submit sẽ là{' '}
                <code className="bg-gray-100 px-1 py-0.5 rounded">
                  {dresBaseUrl}/submit/{'{' }evaluationId{'}'}
                </code>
              </p>
            </div>
          </div>

          {/* Mode toggle */}
          <div>
            <span className="block text-sm font-medium text-gray-700 mb-1">
              Chế độ nộp bài
            </span>
            <div className="inline-flex rounded-md shadow-sm border border-gray-300 overflow-hidden">
              <button
                type="button"
                onClick={() => handleModeChange('KIS')}
                className={`px-4 py-2 text-sm font-medium ${
                  mode === 'KIS'
                    ? 'bg-purple-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                KIS
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('QA')}
                className={`px-4 py-2 text-sm font-medium border-l border-gray-300 ${
                  mode === 'QA'
                    ? 'bg-purple-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                QA
              </button>
              <button
                type="button"
                onClick={() => handleModeChange('TRAKE')}
                className={`px-4 py-2 text-sm font-medium border-l border-gray-300 ${
                  mode === 'TRAKE'
                    ? 'bg-purple-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                TRAKE
              </button>
            </div>
          </div>

          {/* Common fields: video + time (only show time for QA mode) */}
          {mode === 'QA' ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  VIDEO_ID
                </label>
                <input
                  type="text"
                  value={videoId}
                  onChange={(e) => setVideoId(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Ví dụ: L01_V001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  TIME (ms)
                </label>
                <input
                  type="number"
                  value={timeMs}
                  onChange={(e) => setTimeMs(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                VIDEO_ID
              </label>
              <input
                type="text"
                value={videoId}
                onChange={(e) => setVideoId(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Ví dụ: L01_V001"
              />
            </div>
          )}

          {/* Mode specific */}
          {mode === 'QA' ? (
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ANSWER (phần &quot;&lt;ANSWER&gt;&quot; trong ANSWER-QA)
                </label>
                <textarea
                  rows={2}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Nhập câu trả lời QnA..."
                />
              </div>
              {answerQaPreview && (
                <div className="p-2 bg-gray-50 border border-gray-200 rounded-md text-xs text-gray-700">
                  <div className="font-semibold mb-1">ANSWER-QA sẽ gửi:</div>
                  <code className="break-all">{answerQaPreview}</code>
                </div>
              )}
            </div>
          ) : mode === 'TRAKE' ? (
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Frame IDs (phân cách bằng dấu phẩy)
                </label>
                <input
                  type="text"
                  value={frameIds}
                  onChange={(e) => setFrameIds(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Ví dụ: 123,128,140,150"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Nhập danh sách Frame IDs, phân cách bằng dấu phẩy (không có khoảng trắng)
                </p>
              </div>
              {trakePreview && (
                <div className="p-2 bg-gray-50 border border-gray-200 rounded-md text-xs text-gray-700">
                  <div className="font-semibold mb-1">TRAKE sẽ gửi:</div>
                  <code className="break-all">{trakePreview}</code>
                </div>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Start (ms)
                </label>
                <input
                  type="number"
                  value={startMs}
                  onChange={(e) => setStartMs(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  End (ms)
                </label>
                <input
                  type="number"
                  value={endMs}
                  onChange={(e) => setEndMs(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="p-2 bg-red-50 border border-red-200 rounded-md text-xs text-red-700">
              {error}
            </div>
          )}
          {success && (
            <div className="p-2 bg-green-50 border border-green-200 rounded-md text-xs text-green-700">
              {success}
            </div>
          )}
        </form>

        <div className="flex justify-between items-center gap-2 px-4 py-3 border-t bg-gray-50">
          {/* Left side: Login & Get Evaluation buttons */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleLogin}
              disabled={isLoadingSession}
              className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoadingSession ? 'Đang lấy...' : 'Login & Get Session ID'}
            </button>
            <button
              type="button"
              onClick={handleGetEvaluations}
              disabled={isLoadingEvaluation || !sessionId.trim()}
              className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoadingEvaluation ? 'Đang lấy...' : 'Get Evaluation ID'}
            </button>
          </div>

          {/* Right side: Close & Submit buttons */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-100"
            >
              Đóng
            </button>
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Đang nộp...' : 'Submit DRES'}
            </button>
          </div>
        </div>
      </div>
      </div>
      
      {/* Toast Notification */}
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={() => setToast({ ...toast, isVisible: false })}
      />
    </>
  )
}

export default DresSubmitModal


