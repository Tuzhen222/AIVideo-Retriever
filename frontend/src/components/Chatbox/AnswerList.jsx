import React from 'react'

function AnswerList({ submissions, onKeyframeClick, selectedQuery, onQueryFilterChange, uniqueQueries, onFetch, isLoading, onDelete }) {
  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Vừa xong'
    if (diffMins < 60) return `${diffMins} phút trước`
    if (diffHours < 24) return `${diffHours} giờ trước`
    if (diffDays < 7) return `${diffDays} ngày trước`
    
    return date.toLocaleDateString('vi-VN', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    })
  }

  const extractFolderName = (keyframePath) => {
    if (!keyframePath) return null
    
    // Remove leading slash if present
    const cleanPath = keyframePath.startsWith('/') ? keyframePath.substring(1) : keyframePath
    
    // Remove "keyframes/" prefix if present
    const pathWithoutPrefix = cleanPath.startsWith('keyframes/') 
      ? cleanPath.substring('keyframes/'.length) 
      : cleanPath
    
    // Split by '/' and get first part (folder name)
    const parts = pathWithoutPrefix.split('/')
    return parts.length >= 1 ? parts[0] : null
  }

  if (!submissions || submissions.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>Chưa có đáp án nào được submit</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filter and Fetch controls */}
      <div className="p-3 border-b bg-gray-50 space-y-2">
        <div className="flex gap-2">
          <select
            value={selectedQuery || ''}
            onChange={(e) => onQueryFilterChange(e.target.value || null)}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Tất cả queries</option>
            {uniqueQueries.map((query, idx) => (
              <option key={idx} value={query}>
                {query}
              </option>
            ))}
          </select>
          <button
            onClick={onFetch}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            title="Refresh answers"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Loading...</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Fetch</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Submissions list */}
      <div className="flex-1 overflow-y-auto">
        {submissions.map((submission) => (
          <div
            key={submission.id}
            className="p-3 border-b hover:bg-gray-50 transition-colors group relative"
            >
              <div 
                className="flex gap-3 cursor-pointer"
                onClick={() => onKeyframeClick(submission)}
              >
              {/* Keyframe thumbnail */}
              <div className="flex-shrink-0">
                <img
                  src={submission.keyframe_path}
                  alt="Keyframe"
                  className="w-20 h-14 object-cover rounded border border-gray-200"
                  onError={(e) => {
                    e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="80" height="56"%3E%3Crect fill="%23ddd" width="80" height="56"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999" font-size="10"%3ENo Image%3C/text%3E%3C/svg%3E'
                  }}
                />
              </div>
            
            {/* Delete button */}
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (window.confirm(`Bạn có chắc muốn xóa answer này?\nQuery: ${submission.query_text.substring(0, 50)}...`)) {
                    onDelete(submission.id)
                  }
                }}
                className="absolute top-2 right-2 p-1.5 text-red-600 hover:text-red-700 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                title="Xóa answer"
              >
                <svg className="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {submission.query_text}
                  </p>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {formatDate(submission.created_at)}
                  </span>
                </div>

                <div className="text-xs text-gray-600 mb-1">
                  <span className="font-medium">User:</span> {submission.username}
                  {extractFolderName(submission.keyframe_path) && (
                    <>
                      {' • '}
                      <span className="font-medium">Folder:</span> {extractFolderName(submission.keyframe_path)}
                    </>
                  )}
                </div>

                {submission.notes && (
                  <p className="text-xs text-gray-600 italic truncate">
                    {submission.notes}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default AnswerList

