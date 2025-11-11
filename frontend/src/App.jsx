import React, { useState, useRef } from 'react'
import Header from './layouts/Header'
import Sidebar from './layouts/Sidebar'
import MainContent from './layouts/MainContent'
import api from './services/api'

function App() {
  const [hasSearched, setHasSearched] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [querySectionsCount, setQuerySectionsCount] = useState(1)
  const [viewMode, setViewMode] = useState('E')
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState(null)
  const sidebarRef = useRef(null)

  const handleClear = () => {
    // Reset search state
    setHasSearched(false)
    // Clear search results
    setSearchResults(null)
    setSearchError(null)
    // Reset sidebar (query, objects, toggles)
    if (sidebarRef.current) {
      sidebarRef.current.reset()
      setQuerySectionsCount(1)
    }
  }

  /**
   * Combine background info with query sections into a single query string
   */
  const combineQuery = (backgroundInfo, querySections) => {
    const parts = []
    
    // Add background info if exists
    if (backgroundInfo && backgroundInfo.trim() !== '') {
      parts.push(backgroundInfo.trim())
    }
    
    // Add all non-empty query sections
    querySections.forEach((section, index) => {
      if (section.query && section.query.trim() !== '') {
        parts.push(section.query.trim())
      }
    })
    
    // Join with space
    return parts.join(' ')
  }

  const handleSearch = async () => {
    if (!sidebarRef.current) return

    const querySections = sidebarRef.current.getQuerySections()
    const backgroundInfo = sidebarRef.current.getBackgroundInfo()

    // Validate: at least one query section must have a query or background info
    const hasValidQuery = querySections.some(section => section.query.trim() !== '') || 
                         (backgroundInfo && backgroundInfo.trim() !== '')
    if (!hasValidQuery) {
      setSearchError('Please enter at least one query or background info')
      return
    }

    setIsSearching(true)
    setSearchError(null)
    setHasSearched(true)
    setQuerySectionsCount(querySections.length)

    try {
      // Determine search method from toggles
      let searchMethod = 'ensemble'
      const firstSection = querySections[0]
      
      if (firstSection.toggles.asr) {
        searchMethod = 'text' // ASR uses text search
      } else if (firstSection.toggles.multimodal) {
        searchMethod = 'ensemble'
      } else if (firstSection.toggles.ic) {
        searchMethod = 'caption'
      } else if (firstSection.toggles.ocr) {
        searchMethod = 'text'
      } else if (firstSection.toggles.genImage) {
        searchMethod = 'clip' // GenImage uses CLIP
      }

      // Combine background info with query sections into a single query string
      const combinedQuery = combineQuery(backgroundInfo, querySections)
      
      // Build search request
      const searchParams = {
        queries: querySections.map(section => ({
          query: section.query,
          toggles: section.toggles,
          selectedObjects: section.selectedObjects,
        })),
        method: searchMethod,
        top_k: 10,
        filters: {
          objectFilter: firstSection.toggles.objectFilter,
          selectedObjects: firstSection.selectedObjects,
        }
      }

      // Use combined query (background info + all query sections)
      const response = await api.search({
        query: combinedQuery,
        method: searchMethod,
        top_k: 10,
        filters: searchParams.filters,
      })

      setSearchResults(response)
    } catch (error) {
      console.error('Search error:', error)
      setSearchError(error.message || 'Search failed. Please try again.')
      setSearchResults(null)
    } finally {
      setIsSearching(false)
    }
  }

  const handleQuerySectionsChange = (count) => {
    setQuerySectionsCount(count)
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-gray-50">
      {/* Header - Fixed at top */}
      <Header 
        onSearch={handleSearch} 
        onClear={handleClear}
        hasSearched={hasSearched}
        querySectionsCount={querySectionsCount}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        isSearching={isSearching}
      />
      
      {/* Sidebar - Fixed on left */}
      <Sidebar 
        ref={sidebarRef} 
        hasSearched={hasSearched}
        onQuerySectionsChange={handleQuerySectionsChange}
        onSearch={handleSearch}
        isSearching={isSearching}
      />
        
      {/* Main content area - Scrollable */}
      <MainContent 
        searchResults={searchResults} 
        isSearching={isSearching}
        searchError={searchError}
      />
    </div>
  )
}

export default App

