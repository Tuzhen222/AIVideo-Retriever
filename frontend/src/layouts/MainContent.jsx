import React, { useState, useEffect } from 'react'
import VideoModal from '../components/VideoModal'
import TemporalIDResults from '../components/TemporalIDResults'
import TemporalTupleResults from '../components/TemporalTupleResults'
import ImageSearchButton from '../components/ImageSearchButton'
import api from '../services/api'

function MainContent({ searchResults, isSearching = false, searchError = null, onImageClick = null, selectedResult = null, isModalOpen = false, onCloseModal = null, mediaIndex = null, fpsMapping = null, viewMode = 'E', onImageSearch = null }) {
  return (
    <div className="fixed top-6 left-0 md:left-52 right-0 bottom-0 bg-white overflow-y-auto">
      <div className="relative w-full h-full">
      {isSearching ? (
        // Loading state - show overlay if there are existing results, otherwise full screen
        searchResults ? (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-10">
            <div className="text-center">
              <svg className="animate-spin h-12 w-12 text-red-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-gray-600">Searching...</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <svg className="animate-spin h-12 w-12 text-red-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-gray-600">Searching...</p>
            </div>
          </div>
        )
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
      ) : (searchResults?.results?.length > 0 || searchResults?.allMethods || searchResults?.temporalMode) ? ( 
        // Search results
        <div className="p-6" key={`${searchResults.query}-${viewMode}-${Date.now()}`}>
          {/* Temporal results rendering */}
          {searchResults.temporalMode === 'id' ? (
            <div>

              <TemporalIDResults 
                results={searchResults.results}
                onImageClick={onImageClick}
                onImageSearch={onImageSearch}
              />
            </div>
          ) : searchResults.temporalMode === 'tuple' ? (
            <div>
              <TemporalTupleResults 
                tuples={searchResults.results}
                onImageClick={onImageClick}
                onImageSearch={onImageSearch}
              />
            </div>
          ) : viewMode === 'M' && searchResults.allMethods ? (
            /* Mode M: Show separate sections for each method */
            <div className="space-y-8">
              {Object.entries(searchResults.allMethods).map(([methodName, methodResults]) => {
                if (!methodResults || methodResults.length === 0) return null
                
                // Take first 20 results for each method
                const displayResults = methodResults.slice(0, 20)
                
                return (
                  <div key={methodName} className="border-b border-gray-200 pb-6 last:border-b-0">
                    <h3 className="text-lg font-semibold text-gray-800 mb-4 capitalize">
                      {methodName.replace(/_/g, ' ')}
                      <span className="ml-2 text-sm font-normal text-gray-500">({displayResults.length} results)</span>
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2">
                      {displayResults.map((result, index) => (
                        <div 
                          key={result.id || index} 
                          className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow group relative"
                        >
                          {result.keyframe_path && (
                            <div 
                              className="aspect-video bg-gray-100 flex items-center justify-center cursor-pointer hover:opacity-90 transition-opacity relative"
                              onClick={() => onImageClick && onImageClick(result)}
                            >
                              <img 
                                src={result.keyframe_path} 
                                alt={`${methodName} Result ${index + 1}`}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect width="100" height="100" fill="%23ddd"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3ENo Image%3C/text%3E%3C/svg%3E'
                                }}
                              />
                              {onImageSearch && (
                                <ImageSearchButton result={result} onImageSearch={onImageSearch} />
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : searchResults.results && searchResults.results.length > 0 ? (
            /* Mode E or A: Show single grid */
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-2">
              {searchResults.results.map((result, index) => (
                <div 
                  key={result.id || index} 
                  className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow group relative"
                >
                  {result.keyframe_path && (
                    <div 
                      className="aspect-video bg-gray-100 flex items-center justify-center cursor-pointer hover:opacity-90 transition-opacity relative"
                      onClick={() => onImageClick && onImageClick(result)}
                    >
                      <img 
                        src={result.keyframe_path} 
                        alt={`Result ${index + 1}`}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          console.error('[MainContent] Image load failed:', result.keyframe_path)
                          e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect width="100" height="100" fill="%23ddd"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3ENo Image%3C/text%3E%3C/svg%3E'
                        }}
                      />
                      {onImageSearch && (
                        <ImageSearchButton result={result} onImageSearch={onImageSearch} />
                      )}
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

