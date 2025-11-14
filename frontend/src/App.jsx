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
  const [selectedResult, setSelectedResult] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [mediaIndex, setMediaIndex] = useState(null)
  const [fpsMapping, setFpsMapping] = useState(null)
  const sidebarRef = useRef(null)

  // Load search config on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const config = await api.getSearchConfig()
        setSearchConfig(config)
      } catch (err) {
        console.warn('Failed to load search config (fallback to default 200)')
      }
    }
    loadData()
  }, [])

  // Load media index and fps mapping on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [mediaIndexData, fpsMappingData] = await Promise.all([
          api.getMediaIndex(),
          api.getFpsMapping(),
        ])
        setMediaIndex(mediaIndexData)
        setFpsMapping(fpsMappingData)
      } catch (error) {
        console.error('Error loading media index or fps mapping:', error)
      }
    }
    loadData()
  }, [])

  const handleImageClick = (result) => {
    setSelectedResult(result)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedResult(null)
  }

  const handleClear = () => {
    setHasSearched(false)
    setSearchResults(null)
    setSearchError(null)
    if (sidebarRef.current) {
      sidebarRef.current.reset()
      setQuerySectionsCount(1)
    }
  }

  // Utility: avoid undefined toggle cases
  const safeToggle = (toggles, key) => {
    if (!toggles) return false
    if (toggles[key] !== undefined) return toggles[key]
    return false
  }

  // Build final combined query
  const combineQuery = (backgroundInfo, querySections) => {
    const parts = []
    if (backgroundInfo && backgroundInfo.trim() !== "") {
      parts.push(backgroundInfo.trim())
    }

    querySections.forEach(section => {
      // Only add query text (not ocrText here - it's sent separately)
      if (section.query?.trim() !== "") {
        parts.push(section.query.trim())
      }
    })

    return parts.join(" ").trim()
  }

  const handleSearch = async () => {
    if (!sidebarRef.current) return

    const querySections = sidebarRef.current.getQuerySections()
    const backgroundInfo = sidebarRef.current.getBackgroundInfo()

    /** 1) Validate: query required for non-OCR methods, ocrText required for OCR */
    let hasValidationError = false
    let validationMessage = ""

    for (const section of querySections) {
      const t = section.toggles || {}
      const hasQuery = section.query && section.query.trim() !== ""
      const hasOcrText = section.ocrText && section.ocrText.trim() !== ""
      
      // Check if any method requiring query is enabled
      const needsQuery = safeToggle(t, "multimodal") || safeToggle(t, "multiModal") || 
                         safeToggle(t, "ic") || safeToggle(t, "caption") || 
                         safeToggle(t, "asr")
      
      const hasOcrOnly = safeToggle(t, "ocr") && !needsQuery
      
      // If methods requiring query are enabled, query must not be empty
      if (needsQuery && !hasQuery) {
        validationMessage = "Query field is required for Multimodal, IC, and ASR methods"
        hasValidationError = true
        break
      }
      
      // If only OCR is enabled, ocrText must not be empty
      if (hasOcrOnly && !hasOcrText) {
        validationMessage = "OCR text field is required when OCR toggle is enabled"
        hasValidationError = true
        break
      }
    }

    if (hasValidationError) {
      setSearchError(validationMessage)
      return
    }

    /** 2) Validate selected method */
    const firstSection = querySections[0]
    const t = firstSection.toggles || {}

    const hasSelectedMethod =
      safeToggle(t, "multimodal") ||
      safeToggle(t, "multiModal") ||      // support camelCase
      safeToggle(t, "ic") ||
      safeToggle(t, "caption") ||
      safeToggle(t, "asr") ||
      safeToggle(t, "ocr")

    if (!hasSelectedMethod) {
      setSearchError("Please select at least one search method (Multimodal, IC, ASR, or OCR)")
      return
    }

    /** 3) Determine final search method */
    let searchMethod = null

    if (safeToggle(t, "ic") || safeToggle(t, "caption")) {
      searchMethod = "caption"
    } else if (safeToggle(t, "asr")) {
      searchMethod = "text"
    } else if (safeToggle(t, "ocr")) {
      searchMethod = "ocr"
    } else if (safeToggle(t, "multimodal") || safeToggle(t, "multiModal")) {
      searchMethod = "ensemble"
    }

    setIsSearching(true)
    setSearchError(null)
    setHasSearched(true)
    setQuerySectionsCount(querySections.length)

    try {
      const combinedQuery = combineQuery(backgroundInfo, querySections)

      const searchParams = {
        queries: querySections.map(sec => ({
          query: sec.query,
          ocrText: sec.ocrText || "",  // Include ocrText separately
          toggles: sec.toggles,
          selectedObjects: sec.selectedObjects
        })),
        method: searchMethod,
        top_k: null,
        filters: {
          objectFilter: safeToggle(firstSection.toggles, "objectFilter"),
          selectedObjects: firstSection.selectedObjects || []
        }
      }

      console.log('[DEBUG] Query sections:', querySections)
      console.log('[DEBUG] Search params:', searchParams)
      console.log('[DEBUG] Sending to API:', {
        query: combinedQuery,
        method: searchMethod,
        top_k: null,
        filters: searchParams.filters,
        queries: searchParams.queries,
        mode: viewMode
      })

      const response = await api.search({
        query: combinedQuery,
        method: searchMethod,
        top_k: null,
        filters: searchParams.filters,
        queries: searchParams.queries,
        mode: viewMode  // E = ensemble only, A = all methods
      })

      setSearchResults(response)
    } catch (err) {
      console.error("Search error:", err)
      setSearchError(err.message || "Search failed. Please try again.")
      setSearchResults(null)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-gray-50">
      <Header
        onSearch={handleSearch}
        onClear={handleClear}
        hasSearched={hasSearched}
        querySectionsCount={querySectionsCount}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        isSearching={isSearching}
      />

      <Sidebar
        ref={sidebarRef}
        hasSearched={hasSearched}
        onQuerySectionsChange={setQuerySectionsCount}
        onSearch={handleSearch}
        isSearching={isSearching}
      />
      <div className="relative flex-1 overflow-hidden">
        <MainContent
          searchResults={searchResults}
          isSearching={isSearching}
          searchError={searchError}
          onImageClick={handleImageClick}
          selectedResult={selectedResult}
          isModalOpen={isModalOpen}
          onCloseModal={handleCloseModal}
          mediaIndex={mediaIndex}
          fpsMapping={fpsMapping}
        />
      </div>
    </div>
  )
}

export default App
