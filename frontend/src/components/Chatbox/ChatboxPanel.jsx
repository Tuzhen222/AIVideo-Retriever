import React, { useState, useEffect } from 'react'
import AnswerList from './AnswerList'
import SubmitAnswerForm from './SubmitAnswerForm'
import api from '../../services/api'

function ChatboxPanel({ 
  isOpen, 
  onClose, 
  currentQuery = '',
  currentKeyframe = null,
  onKeyframeClick,
  username = 'user1',
  onClearKeyframe = null
}) {
  const [activeTab, setActiveTab] = useState('view') // 'view' or 'submit'
  const [submissions, setSubmissions] = useState([])
  const [uniqueQueries, setUniqueQueries] = useState([])
  const [selectedQuery, setSelectedQuery] = useState(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [autoFetchInterval, setAutoFetchInterval] = useState(null)

  // Auto-switch to submit tab when currentKeyframe is set
  useEffect(() => {
    if (isOpen && currentKeyframe) {
      setActiveTab('submit')
    }
  }, [isOpen, currentKeyframe])

  // Fetch submissions when panel opens or query filter changes
  useEffect(() => {
    if (isOpen && activeTab === 'view') {
      fetchSubmissions()
      fetchUniqueQueries()
      
      // Auto-fetch every 10 seconds
      const interval = setInterval(() => {
        fetchSubmissions()
        fetchUniqueQueries()
      }, 10000) // 10 seconds
      
      setAutoFetchInterval(interval)
      
      return () => {
        if (interval) clearInterval(interval)
      }
    } else {
      // Clear interval when panel closes or tab changes
      if (autoFetchInterval) {
        clearInterval(autoFetchInterval)
        setAutoFetchInterval(null)
      }
    }
  }, [isOpen, activeTab, selectedQuery])

  const fetchSubmissions = async () => {
    setLoading(true)
    try {
      const response = await api.fetchSubmissions({
        query_text: selectedQuery,
        limit: 50,
        offset: 0
      })
      setSubmissions(response.submissions)
    } catch (error) {
      console.error('Error fetching submissions:', error)
      alert('Có lỗi xảy ra khi fetch submissions. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }

  const fetchUniqueQueries = async () => {
    try {
      const response = await api.getUniqueQueries()
      setUniqueQueries(response.queries)
    } catch (error) {
      console.error('Error fetching unique queries:', error)
    }
  }

  const handleFetch = () => {
    fetchSubmissions()
    fetchUniqueQueries()
  }

  const handleSubmit = async (formData) => {
    setSubmitting(true)
    try {
      const response = await api.submitAnswer(formData)
      if (response.success) {
        // Refresh submissions list
        await fetchSubmissions()
        await fetchUniqueQueries()
        // Switch to view tab
        setActiveTab('view')
        // Clear currentKeyframe to prevent auto-switching back to submit tab
        if (onClearKeyframe) {
          onClearKeyframe()
        }
        // Show success message (you can add a toast notification here)
        alert('Submit thành công!')
      }
    } catch (error) {
      console.error('Error submitting answer:', error)
      alert('Có lỗi xảy ra khi submit. Vui lòng thử lại.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (submissionId) => {
    try {
      const response = await api.deleteSubmission(submissionId)
      if (response.success) {
        // Refresh submissions list
        await fetchSubmissions()
        await fetchUniqueQueries()
        alert('Xóa thành công!')
      }
    } catch (error) {
      console.error('Error deleting submission:', error)
      alert('Có lỗi xảy ra khi xóa. Vui lòng thử lại.')
    }
  }

  const handleKeyframeClick = (submission) => {
    // Create a result-like object for VideoModal
    const result = {
      id: submission.result_id,
      keyframe_path: submission.keyframe_path,
      score: 1.0, // Mock score
      video: '', // Will be filled by VideoModal from mediaIndex
      frame_idx: null // Will be extracted from keyframe_path
    }
    
    if (onKeyframeClick) {
      onKeyframeClick(result)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-24 right-6 w-96 h-[600px] bg-white rounded-lg shadow-2xl border border-gray-200 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-blue-600 text-white">
        <h2 className="text-lg font-semibold">Team Answers</h2>
        <button
          onClick={onClose}
          className="text-white hover:text-gray-200 text-xl font-bold leading-none"
        >
          ×
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('view')}
          className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'view'
              ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          View Answers
        </button>
        <button
          onClick={() => setActiveTab('submit')}
          className={`flex-1 px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'submit'
              ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          Submit Answer
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'view' ? (
          loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500">Loading...</div>
            </div>
          ) : (
            <AnswerList
              submissions={submissions}
              onKeyframeClick={handleKeyframeClick}
              selectedQuery={selectedQuery}
              onQueryFilterChange={setSelectedQuery}
              uniqueQueries={uniqueQueries}
              onFetch={handleFetch}
              isLoading={loading}
              onDelete={handleDelete}
            />
          )
        ) : (
          <SubmitAnswerForm
            currentQuery={currentQuery}
            currentKeyframe={currentKeyframe}
            onSubmit={handleSubmit}
            onCancel={() => setActiveTab('view')}
            username={username}
          />
        )}
      </div>
    </div>
  )
}

export default ChatboxPanel

