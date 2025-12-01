import React, { useState, useEffect } from 'react'

function SubmitAnswerForm({ 
  currentQuery = '', 
  currentKeyframe = null, 
  onSubmit, 
  onCancel,
  username = 'user1',
  onOpenDresModal = null
}) {
  const [formData, setFormData] = useState({
    query_text: currentQuery,
    keyframe_path: currentKeyframe?.keyframe_path || '',
    result_id: currentKeyframe?.id ? String(currentKeyframe.id) : '',
    notes: '',
    username: username
  })

  useEffect(() => {
    if (currentQuery) {
      setFormData(prev => ({ ...prev, query_text: currentQuery }))
    }
  }, [currentQuery])

  useEffect(() => {
    if (currentKeyframe) {
      setFormData(prev => ({
        ...prev,
        keyframe_path: currentKeyframe.keyframe_path || '',
        result_id: currentKeyframe.id ? String(currentKeyframe.id) : ''
      }))
    }
  }, [currentKeyframe])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    
    if (!formData.query_text.trim()) {
      alert('Vui lòng nhập query text')
      return
    }
    
    if (!formData.keyframe_path) {
      alert('Vui lòng chọn keyframe từ search results')
      return
    }

    onSubmit(formData)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-800">Submit Answer</h3>
        <p className="text-xs text-gray-600 mt-1">Lưu đáp án keyframe cho query này</p>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Query Text */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Query Text <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            name="query_text"
            value={formData.query_text}
            onChange={handleChange}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Nhập query text..."
            required
          />
        </div>

        {/* Keyframe Preview */}
        {formData.keyframe_path && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Keyframe
            </label>
            <div className="border border-gray-300 rounded-md p-2 bg-gray-50">
              <img
                src={formData.keyframe_path}
                alt="Selected keyframe"
                className="w-full max-w-xs h-auto rounded border border-gray-200"
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="112"%3E%3Crect fill="%23ddd" width="200" height="112"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3ENo Image%3C/text%3E%3C/svg%3E'
                }}
              />
              <p className="text-xs text-gray-600 mt-2 break-all">
                {formData.keyframe_path}
              </p>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              💡 Tip: Chọn keyframe từ search results và click "Save as Answer"
            </p>
          </div>
        )}

        {!formData.keyframe_path && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <p className="text-xs text-yellow-800">
              ⚠️ Chưa chọn keyframe. Vui lòng chọn từ search results trước.
            </p>
          </div>
        )}

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Notes (Optional)
          </label>
          <textarea
            name="notes"
            value={formData.notes}
            onChange={handleChange}
            rows={3}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Thêm ghi chú về đáp án này..."
          />
        </div>

        {/* Username */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Username
          </label>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Nhập username của bạn..."
          />
        </div>
      </form>

      {/* Actions */}
      <div className="p-4 border-t bg-gray-50 flex gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          Cancel
        </button>
        {onOpenDresModal && (
          <button
            type="button"
            onClick={() => {
              onOpenDresModal({
                keyframe_path: formData.keyframe_path,
                query_text: formData.query_text
              })
            }}
            className="flex-1 px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!formData.keyframe_path}
          >
            Submit to DRES
          </button>
        )}
        <button
          type="submit"
          onClick={handleSubmit}
          disabled={!formData.query_text.trim() || !formData.keyframe_path}
          className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Submit
        </button>
      </div>
    </div>
  )
}

export default SubmitAnswerForm

