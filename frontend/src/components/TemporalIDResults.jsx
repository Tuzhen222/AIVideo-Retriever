import React from 'react'

/**
 * Render temporal ID aggregation mode results
 * Simple grid view like normal stage results
 */
function TemporalIDResults({ results, onImageClick }) {
  if (!results || results.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No aggregated results found
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2">
      {results.map((result, index) => (
        <div 
          key={result.id || index}
          className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow"
        >
          {result.keyframe_path && (
            <div 
              className="aspect-video bg-gray-100 flex items-center justify-center cursor-pointer hover:opacity-90 transition-opacity"
              onClick={() => onImageClick && onImageClick(result)}
            >
              <img 
                src={result.keyframe_path} 
                alt={`Result ${index + 1}`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect width="100" height="100" fill="%23ddd"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3ENo Image%3C/text%3E%3C/svg%3E'
                }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default TemporalIDResults
