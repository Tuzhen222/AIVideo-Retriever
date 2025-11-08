import React from 'react'

function SearchButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="px-2 h-full bg-white hover:bg-gray-200 active:bg-gray-300 text-red-600 rounded text-xs font-medium transition-colors duration-200 shadow-sm flex items-center"
    >
      Search
    </button>
  )
}

export default SearchButton

