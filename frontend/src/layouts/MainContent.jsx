import React from 'react'

function MainContent({ searchResults }) {
  return (
    <div className="flex-1 bg-white">
      {searchResults ? (
        // Search results will be displayed here
        <div>
          {/* Search results content */}
        </div>
      ) : (
        // Empty state when no search results
        <div className="flex items-center justify-center h-full text-gray-400">
          {/* Main content - sẽ thêm sau */}
        </div>
      )}
    </div>
  )
}

export default MainContent

