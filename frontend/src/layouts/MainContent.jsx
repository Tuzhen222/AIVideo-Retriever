import React from 'react'

function MainContent({ searchResults }) {
  return (
    <div className="fixed top-6 left-0 md:left-52 right-0 bottom-0 bg-white overflow-y-auto">
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

