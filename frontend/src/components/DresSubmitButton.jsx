import React from 'react'

function DresSubmitButton({ result, onSubmit }) {
  const handleClick = (e) => {
    e.stopPropagation()
    if (onSubmit) {
      onSubmit(result)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="absolute bottom-1 left-1 bg-purple-600 hover:bg-purple-700 text-white p-2 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10"
      title="Submit to DRES"
      aria-label="Submit to DRES"
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
          d="M5 13l4 4L19 7"
        />
      </svg>
    </button>
  )
}

export default DresSubmitButton


