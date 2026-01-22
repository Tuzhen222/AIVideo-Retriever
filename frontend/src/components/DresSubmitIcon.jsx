import React from 'react'

function DresSubmitIcon({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 left-6 w-14 h-14 bg-purple-600 hover:bg-purple-700 text-white rounded-full shadow-lg flex items-center justify-center z-40 transition-all duration-200 hover:scale-110"
      aria-label="Open DRES Submit"
      title="Submit to DRES (Manual Entry)"
    >
      {/* Submit/Check icon SVG */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-6 w-6"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    </button>
  )
}

export default DresSubmitIcon

