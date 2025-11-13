import React, { useState, useRef, useEffect } from 'react'
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
  const [searchConfig, setSearchConfig] = useState({ default_top_k: 200 })
  const sidebarRef = useRef(null)

  // Load search config and mapping files on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const config = await api.getSearchConfig()
        console.log('Loaded search config:', config)
        setSearchConfig(config)
      } catch (err) {
        console.warn('Failed to load search config, using defaults:', err)
        // Keep default_top_k: 200 as fallback (matching backend .env)
      }
    }
    loadData()
  }, [])

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
   * For OCR: if OCR toggle is enabled, use OCR text as the query (or combine with regular query if both exist)
   */
  const combineQuery = (backgroundInfo, querySections) => {
    const parts = []
    
    // Add background info if exists
    if (backgroundInfo && backgroundInfo.trim() !== '') {
      parts.push(backgroundInfo.trim())
    }
    
    // Add all non-empty query sections
    querySections.forEach((section, index) => {
      // If OCR is enabled, prioritize OCR text
      if (section.toggles.ocr && section.ocrText && section.ocrText.trim() !== '') {
        parts.push(section.ocrText.trim())
      }
      // Add regular query if exists (can be combined with OCR text)
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

    // Validate: at least one query section must have a query, OCR text (if OCR is enabled), or background info
    const hasValidQuery = querySections.some(section => {
      const hasQuery = section.query && section.query.trim() !== ''
      const hasOCRText = section.toggles.ocr && section.ocrText && section.ocrText.trim() !== ''
      return hasQuery || hasOCRText
    }) || (backgroundInfo && backgroundInfo.trim() !== '')
    if (!hasValidQuery) {
      setSearchError('Please enter at least one query, OCR text (if OCR is enabled), or background info')
      return
    }

    // Validate: at least one search method must be selected
    const firstSection = querySections[0]
    const hasSelectedMethod = firstSection.toggles.multimodal || 
                              firstSection.toggles.ic || 
                              firstSection.toggles.asr || 
                              firstSection.toggles.ocr
    if (!hasSelectedMethod) {
      setSearchError('Please select at least one search method (Multimodal, IC, ASR, or OCR)')
      return
    }

    let searchMethod = null

    if (firstSection.toggles.asr) {
      searchMethod = 'text' // ASR uses text search (Elasticsearch asr index)
    } else if (firstSection.toggles.ocr) {
      searchMethod = 'ocr' // OCR uses OCR search (Elasticsearch ocr index)
    } else if (firstSection.toggles.multimodal) {
      searchMethod = 'ensemble'
    } else if (firstSection.toggles.ic) {
      searchMethod = 'caption'
    }

    setIsSearching(true)
    setSearchError(null)
    setHasSearched(true)
    setQuerySectionsCount(querySections.length)

    try {
      // Combine background info with query sections into a single query string
      const combinedQuery = combineQuery(backgroundInfo, querySections)
      
      // Build search request - let backend use DEFAULT_TOP_K by sending null
      // User can set DEFAULT_TOP_K in backend .env file if they want more results
      const searchParams = {
        queries: querySections.map(section => ({
          query: section.query,
          toggles: section.toggles,
          selectedObjects: section.selectedObjects,
        })),
        method: searchMethod,
        top_k: null, // Let backend use DEFAULT_TOP_K
        filters: {
          objectFilter: firstSection.toggles.objectFilter,
          selectedObjects: firstSection.selectedObjects,
        }
      }

      // Use combined query (background info + all query sections)
      const response = await api.search({
        query: combinedQuery,
        method: searchMethod,
        top_k: null, // Let backend use DEFAULT_TOP_K
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

