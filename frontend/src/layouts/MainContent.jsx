import React, { useState, useEffect } from 'react'
import VideoModal from '../components/VideoModal'
import api from '../services/api'

function MainContent({ searchResults, isSearching = false, searchError = null, onImageClick = null, selectedResult = null, isModalOpen = false, onCloseModal = null, mediaIndex = null, fpsMapping = null }) {
  return (
    <div className="fixed top-6 left-0 md:left-52 right-0 bottom-0 bg-white overflow-y-auto">
      <div className="relative w-full h-full">
      {isSearching ? (
        // Loading state
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <svg className="animate-spin h-12 w-12 text-red-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-gray-600">Searching...</p>
          </div>
        </div>
      ) : searchError ? (
        // Error state
        <div className="flex items-center justify-center h-full">
          <div className="text-center p-6 bg-red-50 border border-red-200 rounded-lg max-w-md">
            <svg className="h-12 w-12 text-red-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="text-lg font-semibold text-red-800 mb-2">Search Error</h3>
            <p className="text-red-600">{searchError}</p>
          </div>
        </div>
      ) : searchResults ? (
        // Search results
        <div className="p-6">          
          {searchResults.results && searchResults.results.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2">
              {searchResults.results.map((result, index) => (
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
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500">No results found</p>
            </div>
          )}
        </div>
      ) : (
        // Empty state when no search results
        <div className="flex items-center justify-center h-full text-gray-400">
          <div className="text-center">
            <svg className="h-16 w-16 mx-auto mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-lg">Enter a query and click Search to begin</p>
          </div>
        </div>
      )}

      {/* Video Modal */}
      <VideoModal
        result={selectedResult}
        isOpen={isModalOpen}
        onClose={onCloseModal}
        mediaIndex={mediaIndex}
        fpsMapping={fpsMapping}
      />
      </div>
    </div>
  )
}

export default MainContent

