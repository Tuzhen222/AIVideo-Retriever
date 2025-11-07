import React from 'react'

function SearchButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="px-2 h-full bg-white hover:bg-gray-100 text-red-600 rounded text-xs font-medium transition-colors shadow-sm flex items-center"
    >
      Search
    </button>
  )
}

export default SearchButton

