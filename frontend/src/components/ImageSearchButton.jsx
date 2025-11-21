import React from 'react'

/**
 * Button to trigger image search for a specific result image
 * Appears on hover over each result image
 */
function ImageSearchButton({ onImageSearch, result }) {
  const handleClick = (e) => {
    e.stopPropagation() // Prevent triggering image modal
    if (onImageSearch) {
      onImageSearch(result)
    }
  }

  return (
    <button
      onClick={handleClick}
      className="absolute top-1 right-1 bg-blue-600 hover:bg-blue-700 text-white p-1.5 rounded-full shadow-lg transition-all duration-200 opacity-0 group-hover:opacity-100"
      title="Search similar images"
    >
      <svg 
        className="w-4 h-4" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
        />
      </svg>
    </button>
  )
}

export default ImageSearchButton
