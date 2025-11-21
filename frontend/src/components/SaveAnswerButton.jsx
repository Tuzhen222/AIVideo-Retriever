import React from 'react'

function SaveAnswerButton({ result, onSave }) {
  const handleClick = (e) => {
    e.stopPropagation() // Prevent triggering parent onClick
    if (onSave) {
      onSave(result)
    }
  }

  return (
    <button
      onClick={handleClick}
      className="absolute top-2 right-2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10"
      title="Save as Answer"
      aria-label="Save as Answer"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
        />
      </svg>
    </button>
  )
}

export default SaveAnswerButton

