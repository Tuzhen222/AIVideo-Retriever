import React from 'react'

function Toast({ message, type = 'info', isVisible, onClose }) {
  if (!isVisible) return null

  const bgColor = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-yellow-500'
  }[type] || 'bg-gray-500'

  // Format message as JSON if it's an object, otherwise display as string
  const displayMessage = typeof message === 'object' 
    ? JSON.stringify(message, null, 2)
    : message

  return (
    <div
      className={`fixed top-4 right-4 z-[100] min-w-[300px] max-w-[600px] ${bgColor} text-white rounded-lg shadow-2xl transform transition-all duration-300 ease-in-out translate-x-0 opacity-100`}
    >
      <div className="p-4 flex items-start justify-between gap-3">
        <div className="flex-1 overflow-auto max-h-[400px]">
          <div className="font-semibold mb-2 text-sm">
            {type === 'success' && '✓ Thành công'}
            {type === 'error' && '✗ Lỗi'}
            {type === 'info' && 'ℹ Thông tin'}
            {type === 'warning' && '⚠ Cảnh báo'}
          </div>
          <div className="text-xs font-mono whitespace-pre-wrap break-words bg-black bg-opacity-20 p-2 rounded overflow-x-auto">
            {displayMessage}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-white hover:text-gray-200 text-xl font-bold leading-none flex-shrink-0"
          title="Đóng"
        >
          ×
        </button>
      </div>
    </div>
  )
}

export default Toast

