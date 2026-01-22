import React from 'react'

function SearchButton({ onClick, isSearching = false, disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || isSearching}
      className="px-2 h-full bg-white hover:bg-gray-200 active:bg-gray-300 text-red-600 rounded text-xs font-medium transition-colors duration-200 shadow-sm flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {isSearching ? (
        <>
          <svg className="animate-spin -ml-1 mr-1 h-3 w-3 text-red-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Searching...
        </>
      ) : (
        'Search'
      )}
    </button>
  )
}

export default SearchButton

