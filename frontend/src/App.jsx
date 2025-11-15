import React, { useState, useRef, useEffect } from 'react'
import Header from './layouts/Header'
import Sidebar from './layouts/Sidebar'
import MainContent from './layouts/MainContent'
import api from './services/api'

function App() {
  const [hasSearched, setHasSearched] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [fullResponse, setFullResponse] = useState(null)  // Store full query_0/1/2/3 response
  const [selectedQ, setSelectedQ] = useState('Q0')
  const [selectedStage, setSelectedStage] = useState(1)  // For multistage results
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
    setFullResponse(null)
    setSelectedQ('Q0')
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

  // Extract results for display based on selectedQ and viewMode
  const extractResultsForDisplay = (response, selectedQ, viewMode, selectedStage = 1) => {
    if (!response) return null

    // Check if this is a multistage response
    if (response.stages && Array.isArray(response.stages)) {
      // Multistage response format
      const stage = response.stages.find(s => s.stage_id === selectedStage) || response.stages[0]
      
      if (!stage) {
        console.warn('[DEBUG] No stage found for selectedStage:', selectedStage)
        return null
      }

      // Map Q button to query field
      const queryMap = {
        'Q0': 'query_0',
        'Q1': 'query_1',
        'Q2': 'query_2'
      }

      const queryKey = queryMap[selectedQ] || 'query_0'
      const queryText = stage[queryKey] || stage.query_original

      console.log(`[DEBUG MULTISTAGE] Stage ${selectedStage}, ${selectedQ} => ${queryText}`)

      // For multistage, results are already ensembled per stage
      // Mode E: Show stage ensemble results
      if (viewMode === 'E') {
        return {
          results: stage.results || [],
          query: queryText,
          method: (stage.enabled_methods || []).join('+'),
          total: stage.total || 0,
          stageInfo: {
            stage_id: stage.stage_id,
            stage_name: stage.stage_name,
            enabled_methods: stage.enabled_methods
          }
        }
      }

      // Mode A: Show per-method results for stage
      if (viewMode === 'A' && stage.per_method_results) {
        return {
          results: stage.results || [],
          query: queryText,
          method: (stage.enabled_methods || []).join('+'),
          total: stage.total || 0,
          allMethods: stage.per_method_results,
          stageInfo: {
            stage_id: stage.stage_id,
            stage_name: stage.stage_name,
            enabled_methods: stage.enabled_methods
          }
        }
      }

      // Fallback for multistage
      return {
        results: stage.results || [],
        query: queryText,
        method: (stage.enabled_methods || []).join('+'),
        total: stage.total || 0
      }
    }

    // Original augmented search response format (query_0/1/2/3)
    const queryMap = {
      'Q0': 'query_0',
      'Q1': 'query_1', 
      'Q2': 'query_2',
      'Q3': 'query_3'
    }

    const queryKey = queryMap[selectedQ]
    const queryData = response[queryKey]

    if (!queryData || !queryData.methods) {
      console.warn(`[DEBUG] No data for ${selectedQ}`)
      return null
    }

    // Mode E: Show only ensemble_of_ensemble
    if (viewMode === 'E') {
      const results = queryKey === 'query_3' 
        ? queryData.methods.ensemble_of_ensemble || []
        : queryData.methods.ensemble || []
      
      return {
        results,
        query: queryData.text || response.original_query,
        method: response.method,
        total: results.length
      }
    }

    // Mode A: Show ensemble for selected query
    if (viewMode === 'A') {
      const results = queryKey === 'query_3'
        ? queryData.methods.ensemble_of_ensemble || []
        : queryData.methods.ensemble || []

      return {
        results,
        query: queryData.text || response.original_query,
        method: response.method,
        total: results.length
      }
    }

    // Mode M: Show all methods for selected query (20 each)
    if (viewMode === 'M') {
      return {
        results: [],  // No single grid
        query: queryData.text || response.original_query,
        method: response.method,
        total: 0,
        allMethods: queryData.methods  // All methods for separate sections
      }
    }

    // Fallback
    return {
      results: [],
      query: queryData.text || response.original_query,
      method: response.method,
      total: 0
    }
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
      let response

      // Multi-stage search: call multistage endpoint
      if (querySections.length > 1) {
        console.log('[DEBUG] Using multistage search for', querySections.length, 'stages')
        
        const stages = querySections.map((sec, index) => ({
          stage_id: index + 1,
          stage_name: `Stage ${index + 1}`,
          query: sec.query || "",
          ocr_text: sec.ocrText || "",
          toggles: sec.toggles || {},
          selected_objects: sec.selectedObjects || []
        }))

        console.log('[DEBUG] Multistage stages:', stages)

        response = await api.searchMultistage(stages, {
          top_k: null,
          mode: viewMode  // E = ensemble only, A = all methods
        })

        console.log('[DEBUG] Multistage backend response:', response)
      }
      // Single query: use old API
      else {
        const combinedQuery = combineQuery(backgroundInfo, querySections)

        const searchParams = {
          queries: querySections.map(sec => ({
            query: sec.query,
            ocrText: sec.ocrText || "",
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

        console.log('[DEBUG] Single query search params:', searchParams)

        response = await api.search({
          query: combinedQuery,
          method: searchMethod,
          top_k: null,
          filters: searchParams.filters,
          queries: searchParams.queries,
          mode: viewMode
        })

        console.log('[DEBUG] Single query backend response:', response)
      }

      // Store full response with query_0/1/2/3
      setFullResponse(response)
      
      // Extract results based on current selectedQ and viewMode
      const transformedResults = extractResultsForDisplay(response, selectedQ, viewMode, selectedStage)
      console.log('[DEBUG] Transformed results for display:', transformedResults)
      setSearchResults(transformedResults)
    } catch (err) {
      console.error("Search error:", err)
      setSearchError(err.message || "Search failed. Please try again.")
      setSearchResults(null)
    } finally {
      setIsSearching(false)
    }
  }

  // Update display when selectedQ changes
  useEffect(() => {
    if (fullResponse) {
      const transformedResults = extractResultsForDisplay(fullResponse, selectedQ, viewMode, selectedStage)
      setSearchResults(transformedResults)
    }
  }, [selectedQ, viewMode, fullResponse, selectedStage])

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
        selectedQ={selectedQ}
        onQChange={setSelectedQ}
        selectedStage={selectedStage}
        onStageChange={setSelectedStage}
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
          viewMode={viewMode}
        />
      </div>
    </div>
  )
}

export default App
