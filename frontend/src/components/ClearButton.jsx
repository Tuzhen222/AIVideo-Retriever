import React from 'react'

function ClearButton({ onClick, disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-2 h-full bg-white hover:bg-gray-200 active:bg-gray-300 text-red-600 rounded text-xs font-medium transition-colors duration-200 shadow-sm flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
    >
      Clear
    </button>
  )
}

export default ClearButton

