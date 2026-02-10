import React from 'react'
import ImageSearchButton from './ImageSearchButton'
import SaveAnswerButton from './SaveAnswerButton'
import DresSubmitButton from './DresSubmitButton'

/**
 * Render temporal tuple mode results
 * Shows grouped sequences of frames from different stages (same video, increasing frame indices)
 */
function TemporalTupleResults({ tuples, onImageClick, onImageSearch, onSaveAnswer, onDresSubmitClick = null, onTupleSubmit = null }) {
  if (!tuples || tuples.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-lg font-semibold mb-2">No temporal sequences found</p>
        <p className="text-sm">Try adjusting your search queries or check if results exist in the same video.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {tuples.map((tuple, tupleIndex) => {
        const { tuple_id, video, results, frame_indices, total_score, num_stages } = tuple
        
        return (
          <div 
            key={tuple_id || tupleIndex}
            className="border-4 border-red-600 rounded-lg p-2 bg-white hover:shadow-lg transition-shadow"
          >
            {/* Images stacked vertically in the red box */}
            <div className="space-y-2">
              {results?.map((result, stageIdx) => {
                const frameIdx = frame_indices?.[stageIdx]
                
                return (
                  <div 
                    key={result.id || stageIdx}
                    className="bg-gray-50 rounded overflow-hidden group relative"
                  >
                    {/* Keyframe */}
                    {result.keyframe_path && (
                      <div 
                        className="aspect-video bg-gray-100 cursor-pointer hover:opacity-90 transition-opacity relative"
                        onClick={() => onImageClick && onImageClick(result)}
                      >
                        <img 
                          src={result.keyframe_path} 
                          alt={`Frame ${frameIdx}`}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="60"%3E%3Crect width="100" height="60" fill="%23ddd"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999" font-size="10"%3ENo Image%3C/text%3E%3C/svg%3E'
                          }}
                        />
                        {onImageSearch && (
                          <ImageSearchButton result={result} onImageSearch={onImageSearch} />
                        )}
                        {onSaveAnswer && (
                          <SaveAnswerButton result={result} onSave={onSaveAnswer} />
                        )}
                        {onDresSubmitClick && (
                          <DresSubmitButton result={result} onSubmit={onDresSubmitClick} />
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
            {/* Submit Tuple Button - nằm giữa ô đỏ */}
            {onTupleSubmit && frame_indices && frame_indices.length > 0 && (
              <div className="mt-2 pt-2 border-t border-red-300">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onTupleSubmit({ video, frame_indices })
                  }}
                  className="w-full bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium py-2 px-3 rounded transition-colors"
                  title="Submit toàn bộ tuple này vào DRES (TRAKE mode)"
                >
                  Submit Tuple to DRES
                </button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default TemporalTupleResults
