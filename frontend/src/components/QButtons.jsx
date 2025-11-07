import React from 'react'

function QButtons({ onQClick, selectedQ }) {
  const qButtons = ['Q0', 'Q1', 'Q2', 'Q3']

  return (
    <div className="flex items-center gap-1">
      {qButtons.map((q) => (
        <button
          key={q}
          onClick={() => onQClick && onQClick(q)}
          className={`px-2 h-full rounded text-xs font-medium transition-colors flex items-center border ${
            selectedQ === q
              ? 'bg-red-100 border-red-400 text-red-700 border-dashed'
              : 'bg-white border-gray-300 text-gray-800 hover:bg-gray-100'
          }`}
        >
          {q}
        </button>
      ))}
    </div>
  )
}

export default QButtons

