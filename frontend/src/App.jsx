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
  const [temporalMode, setTemporalMode] = useState('id')  // 'id' or 'tuple'
  const [isMultiStage, setIsMultiStage] = useState(false)
  const [imageSearchActive, setImageSearchActive] = useState(false)  // Image search mode
  const [imageSearchImage, setImageSearchImage] = useState(null)  // Source image for search
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

  // Check for image search URL parameter on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const imageSearchPath = urlParams.get('imageSearch')
    
    // Only run if we have the URL parameter AND config is loaded AND we haven't already searched
    if (imageSearchPath && searchConfig.default_top_k && !hasSearched) {
      console.log('[App] Image search from URL parameter:', imageSearchPath)
      
      // Auto-trigger image search
      const performImageSearch = async () => {
        setIsSearching(true)
        setSearchError(null)
        setImageSearchActive(true)
        
        try {
          const response = await api.searchByImage(imageSearchPath, searchConfig.default_top_k || 200)
          
          console.log('[App] Image search response:', response)
          console.log('[App] First result keyframe_path:', response.results?.[0]?.keyframe_path)

          // Backend already converts paths to /keyframes/ format
          // No need to transform again, just use as-is
          const transformedResults = {
            results: response.results || [],
            query: `Similar images to: ${imageSearchPath.split('/').pop()}`,
            method: 'clip-image',
            total: response.total || 0,
            queryImage: imageSearchPath
          }
          
          console.log('[App] Transformed results:', transformedResults)
          console.log('[App] First transformed result:', transformedResults.results?.[0])

          setSearchResults(transformedResults)
          setHasSearched(true)
          setImageSearchImage({ keyframe_path: imageSearchPath })
        } catch (err) {
          console.error('[App] Image search error:', err)
          setSearchError(err.message || 'Image search failed')
        } finally {
          setIsSearching(false)
        }
      }
      
      performImageSearch()
    }
  }, [searchConfig.default_top_k, hasSearched])

  // Re-extract results when viewMode, selectedQ, or selectedStage changes
  useEffect(() => {
    if (fullResponse && hasSearched) {
      console.log('[App] Re-extracting results due to viewMode/Q/Stage change')
      console.log('[App] Current viewMode:', viewMode, 'fullResponse has per_method_results:', !!fullResponse.per_method_results)
      
      const transformedResults = extractResultsForDisplay(fullResponse, selectedQ, viewMode, selectedStage, temporalMode)
      console.log('[App] Transformed results:', transformedResults)
      setSearchResults(transformedResults)
    }
  }, [viewMode, selectedQ, selectedStage, temporalMode, fullResponse, hasSearched])

  const handleImageClick = (result) => {
    console.log('[App.handleImageClick] Clicked result:', result)
    setSelectedResult(result)
    setIsModalOpen(true)
    console.log('[App.handleImageClick] Modal should open now')
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedResult(null)
  }

  const handleTemporalModeChange = async (newMode) => {
    console.log('[App] Temporal mode changed to:', newMode)
    setTemporalMode(newMode)
    
    // Re-fetch search with new temporal mode if multistage
    if (isMultiStage && sidebarRef.current && hasSearched) {
      console.log('[App] Re-fetching with new temporal mode:', newMode)
      const querySections = sidebarRef.current.getQuerySections()
      
      setIsSearching(true)
      try {
        const stages = querySections.map((sec, index) => ({
          stage_id: index + 1,
          stage_name: `Stage ${index + 1}`,
          query: sec.query || "",
          ocr_text: sec.ocrText || "",
          toggles: sec.toggles || {},
          selected_objects: sec.selectedObjects || []
        }))

        const response = await api.searchMultistage(stages, {
          top_k: null,
          mode: viewMode,
          temporal_mode: newMode
        })

        setFullResponse(response)
        const transformedResults = extractResultsForDisplay(response, selectedQ, viewMode, selectedStage, newMode)
        setSearchResults(transformedResults)
      } catch (err) {
        console.error('[App] Error re-fetching with new temporal mode:', err)
      } finally {
        setIsSearching(false)
      }
    }
  }

  const handleClear = () => {
    setHasSearched(false)
    setSearchResults(null)
    setFullResponse(null)
    setSelectedQ('Q0')
    setSearchError(null)
    setTemporalMode('id')  // Reset to ID mode
    setIsMultiStage(false)
    setSelectedStage(1)
    setImageSearchActive(false)
    setImageSearchImage(null)
    if (sidebarRef.current) {
      sidebarRef.current.reset()
      setQuerySectionsCount(1)
    }
  }

  const handleImageSearch = async (result) => {
    console.log('[App] Image search triggered for:', result)
    
    if (!result || !result.keyframe_path) {
      console.error('[App] Invalid result for image search')
      return
    }

    // Open image search in new tab
    // Encode the keyframe path as query parameter
    const encodedPath = encodeURIComponent(result.keyframe_path)
    const newTabUrl = `${window.location.origin}${window.location.pathname}?imageSearch=${encodedPath}`
    
    console.log('[App] Opening image search in new tab:', newTabUrl)
    window.open(newTabUrl, '_blank')
  }

  // Utility: avoid undefined toggle cases
  const safeToggle = (toggles, key) => {
    if (!toggles) return false
    if (toggles[key] !== undefined) return toggles[key]
    return false
  }

  // Extract results for display based on selectedQ and viewMode
  const extractResultsForDisplay = (response, selectedQ, viewMode, selectedStage = 1, temporalMode = 'id') => {
    if (!response) return null

    // Check if this is a multistage response
    if (response.stages && Array.isArray(response.stages)) {
      // Check if viewing temporal aggregation (Temporal Result stage)
      if (response.temporal_aggregation && selectedStage === 'temporal') {
        console.log('[DEBUG TEMPORAL] Viewing temporal aggregation:', temporalMode)
        
        const tempAgg = response.temporal_aggregation
        
        if (temporalMode === 'id' && tempAgg.mode === 'id') {
          // ID aggregation mode
          return {
            results: tempAgg.results || [],
            query: 'Temporal Aggregation (ID Mode)',
            method: 'temporal_id',
            total: tempAgg.total || 0,
            temporalMode: 'id'
          }
        } else if (temporalMode === 'tuple' && tempAgg.mode === 'tuple') {
          // Tuple mode
          return {
            results: tempAgg.tuples || [],
            query: 'Temporal Aggregation (Tuple Mode)',
            method: 'temporal_tuple',
            total: tempAgg.total || 0,
            temporalMode: 'tuple'
          }
        }
        
        // Fallback if mode mismatch - re-fetch needed
        return {
          results: [],
          query: 'Temporal Aggregation',
          method: 'temporal',
          total: 0,
          temporalMode: temporalMode
        }
      }
      
      // Regular stage view
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

      console.log(`[DEBUG MULTISTAGE] Stage ${selectedStage}, ViewMode=${viewMode}, Q=${selectedQ}, Query="${queryText}"`)

      // Mode E: Show ensemble results (Q0+Q1+Q2 combined) - ignore Q button
      if (viewMode === 'E') {
        return {
          results: stage.results || [],
          query: stage.query_original || stage.query_0,
          method: (stage.enabled_methods || []).join('+'),
          total: stage.total || 0,
          stageInfo: {
            stage_id: stage.stage_id,
            stage_name: stage.stage_name,
            enabled_methods: stage.enabled_methods
          }
        }
      }

      // Mode A: Show ensemble for selected Q (Q0/Q1/Q2), with Q button active
      if (viewMode === 'A') {
        // Use individual query results based on selectedQ
        let queryResults = stage.results || []  // Fallback to ensemble
        
        if (selectedQ === 'Q0' && stage.q0_results) {
          queryResults = stage.q0_results
        } else if (selectedQ === 'Q1' && stage.q1_results) {
          queryResults = stage.q1_results
        } else if (selectedQ === 'Q2' && stage.q2_results) {
          queryResults = stage.q2_results
        }
        
        return {
          results: queryResults,
          query: queryText,
          method: (stage.enabled_methods || []).join('+'),
          total: queryResults.length,
          stageInfo: {
            stage_id: stage.stage_id,
            stage_name: stage.stage_name,
            enabled_methods: stage.enabled_methods
          }
        }
      }

      // Mode M: Show per-method results for selected Q
      if (viewMode === 'M' && stage.per_method_results) {
        return {
          results: [],  // No single grid in mode M
          query: queryText,
          method: (stage.enabled_methods || []).join('+'),
          total: 0,
          allMethods: stage.per_method_results,  // Show separate sections per method
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

    // Check if this is an augmented search response (query_0/1/2/3 structure)
    const queryMap = {
      'Q0': 'query_0',
      'Q1': 'query_1', 
      'Q2': 'query_2',
      'Q3': 'query_3'
    }

    const queryKey = queryMap[selectedQ]
    const queryData = response[queryKey]

    // If we have queryData with methods, use augmented response format
    if (queryData && queryData.methods) {
      // Mode E: Show only ensemble_of_ensemble
      if (viewMode === 'E') {
        const results = queryKey === 'query_3' 
          ? queryData.methods.ensemble_of_ensemble || []
          : queryData.methods.ensemble || []
        
        return {
          results,
          query: queryData.text || response.original_query || response.query,
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
          query: queryData.text || response.original_query || response.query,
          method: response.method,
          total: results.length
        }
      }

      // Mode M: Show all methods for selected query (20 each)
      if (viewMode === 'M') {
        return {
          results: [],  // No single grid
          query: queryData.text || response.original_query || response.query,
          method: response.method,
          total: 0,
          allMethods: queryData.methods  // All methods for separate sections
        }
      }
    }

    // Simple response format (direct results array from /api/search)
    // This is the standard response from the backend: { results, total, query, method, per_method_results }
    console.log('[DEBUG] Using simple response format')
    
    if (viewMode === 'M' && response.per_method_results) {
      // Mode M: Show per-method results
      return {
        results: [],
        query: response.query,
        method: response.method,
        total: response.total || 0,
        allMethods: response.per_method_results
      }
    }

    // Mode E or A: Show combined results
    return {
      results: response.results || [],
      query: response.query,
      method: response.method,
      total: response.total || 0
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

        setIsMultiStage(true)

        response = await api.searchMultistage(stages, {
          top_k: null,
          mode: viewMode,  // E = ensemble only, A = all methods
          temporal_mode: querySections.length > 1 ? temporalMode : null  // Only use temporal for multistage
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
        temporalMode={temporalMode}
        onTemporalModeChange={handleTemporalModeChange}
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
          onImageSearch={handleImageSearch}
        />
      </div>
    </div>
  )
}

export default App
