import React, { useState, useImperativeHandle, forwardRef, useEffect } from 'react'
import ToggleButton from '../components/ToggleButton'
import ObjectSelector from '../components/ObjectSelector'

const Sidebar = forwardRef(function Sidebar(
  { hasSearched, onQuerySectionsChange, onSearch, isSearching = false, onImageUploadSearch = null },
  ref
) {
  const [isOpen, setIsOpen] = useState(true)
  const [backgroundInfo, setBackgroundInfo] = useState('')
  const [useAugmented, setUseAugmented] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  
  // State for multiple query sections
  const [querySections, setQuerySections] = useState([
    {
      id: 1,
      query: '',
      ocrText: '',
      selectedObjects: [],
      toggles: {
        multimodal: false,
        ic: false,
        asr: false,
        ocr: false,
        objectFilter: false,
      }
    }
  ])

  // Expose reset function and query sections count to parent component
  useImperativeHandle(ref, () => ({
    reset: () => {
      setBackgroundInfo('')
      setQuerySections([{
        id: 1,
        query: '',
        ocrText: '',
        selectedObjects: [],
        toggles: {
          multimodal: false,
          ic: false,
          asr: false,
          ocr: false,
          objectFilter: false,
        }
      }])
      setUseAugmented(false)
    },
    getQuerySectionsCount: () => querySections.length,
    getQuerySections: () => querySections,
    getBackgroundInfo: () => backgroundInfo,
    getUseAugmented: () => useAugmented,
    setUseAugmented: (value) => setUseAugmented(value)
  }))

  // Notify parent when query sections change
  React.useEffect(() => {
    if (onQuerySectionsChange) {
      onQuerySectionsChange(querySections.length)
    }
  }, [querySections.length, onQuerySectionsChange])

  // Handle paste from clipboard
  useEffect(() => {
    const handlePaste = async (e) => {
      // Only handle if image upload search is available
      if (!onImageUploadSearch) return

      const items = e.clipboardData?.items
      if (!items) return

      // Find image in clipboard
      for (let i = 0; i < items.length; i++) {
        const item = items[i]
        if (item.type.indexOf('image') !== -1) {
          e.preventDefault()
          
          const blob = item.getAsFile()
          if (!blob) continue

          // Convert blob to File object
          const file = new File([blob], `pasted-image-${Date.now()}.png`, {
            type: blob.type || 'image/png'
          })

          console.log('[Sidebar] Pasted image from clipboard:', file.name, file.size, 'bytes')
          
          // Set file and auto-trigger search
          setUploadFile(file)
          
          // Auto-trigger search after a short delay to ensure state is updated
          setTimeout(() => {
            if (onImageUploadSearch) {
              onImageUploadSearch(file)
            }
          }, 100)
          
          break
        }
      }
    }

    // Add paste event listener
    window.addEventListener('paste', handlePaste)
    
    return () => {
      window.removeEventListener('paste', handlePaste)
    }
  }, [onImageUploadSearch])

  // Add new query section
  const addQuerySection = () => {
    const newId = Math.max(...querySections.map(s => s.id), 0) + 1
    setQuerySections([...querySections, {
      id: newId,
      query: '',
      ocrText: '',
      selectedObjects: [],
      toggles: {
        multimodal: false,
        ic: false,
        asr: false,
        ocr: false,
        objectFilter: false,
      }
    }])
  }

  // Remove query section
  const removeQuerySection = (id) => {
    if (querySections.length > 1) {
      setQuerySections(querySections.filter(section => section.id !== id))
    }
  }

  // Update query section
  const updateQuerySection = (id, updates) => {
    setQuerySections(querySections.map(section => 
      section.id === id ? { ...section, ...updates } : section
    ))
  }

  // Handle toggle for a specific query section
  const handleToggle = (id, key) => {
    const section = querySections.find(s => s.id === id)
    if (!section) return

    // Object toggle can only be turned on if user has searched
    if (key === 'objectFilter' && !hasSearched && !section.toggles[key]) {
      return // Prevent turning on if hasn't searched
    }
    
    const newToggles = { ...section.toggles }
    
    // Object filter is independent - it can work with ASR or other toggles
    if (key === 'objectFilter') {
      newToggles[key] = !section.toggles[key]
    }
    // If ASR is being turned on
    else if (key === 'asr' && !section.toggles.asr) {
      // Turn off other search method toggles (but keep objectFilter)
      newToggles.multimodal = false
      newToggles.ic = false
      newToggles.ocr = false
      newToggles.asr = true
    }
    // If any other search method toggle is being turned on (excluding objectFilter)
    else if (key !== 'asr' && key !== 'objectFilter') {
      // Turn off ASR (if it was on) - ASR cannot coexist with other methods
      if (section.toggles.asr) {
        newToggles.asr = false
      }
      // Toggle this key (allow multiple non-ASR methods)
      newToggles[key] = !section.toggles[key]
    }
    // If toggling off, just update that toggle
    else {
      newToggles[key] = !section.toggles[key]
    }
    
    updateQuerySection(id, { toggles: newToggles })
  }

  // If hasSearched becomes false, turn off all objectFilters
  React.useEffect(() => {
    if (!hasSearched) {
      setQuerySections(querySections.map(section => ({
        ...section,
        toggles: {
          ...section.toggles,
          objectFilter: false
        }
      })))
    }
  }, [hasSearched])

  // Handle Enter key press for search
  const handleKeyDown = (e, isBackgroundInfo = false) => {
    // Enter without Shift triggers search
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (onSearch && !isSearching) {
        onSearch()
      }
    }
    // Shift+Enter allows newline (default behavior)
  }

  // Auto-resize textarea function
  const autoResizeTextarea = (e, maxHeight = null) => {
    const textarea = e.target
    textarea.style.height = 'auto'
    const scrollHeight = textarea.scrollHeight
    
    if (maxHeight && scrollHeight > maxHeight) {
      // If exceeds max height, set to max and enable scroll
      textarea.style.height = `${maxHeight}px`
      textarea.style.overflowY = 'auto'
    } else {
      // Otherwise, resize to content and disable scroll
      textarea.style.height = `${scrollHeight}px`
      textarea.style.overflowY = 'hidden'
    }
  }

  return (
    <>
      {/* Mobile toggle button - chỉ hiện trên mobile */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed top-6 left-0 z-50 bg-red-500 text-white p-2 rounded-r-lg shadow-lg"
        aria-label="Toggle sidebar"
      >
        {isOpen ? '◀' : '▶'}
      </button>

      {/* Sidebar */}
      <div
        className={`
          bg-white border-r border-gray-200
          transition-all duration-300 ease-in-out
          overflow-y-auto
          w-52
          fixed top-6 bottom-0 left-0 z-40
          ${isOpen ? 'block' : 'hidden md:block'}
        `}
      >
        <div className="p-3 space-y-3">
          {/* Background Info div */}
          <div className="border-2 border-gray-300 rounded-lg bg-white shadow-sm p-2">
            <textarea
              value={backgroundInfo}
              onChange={(e) => {
                setBackgroundInfo(e.target.value)
                autoResizeTextarea(e, 200)
              }}
              onKeyDown={(e) => handleKeyDown(e, true)}
              placeholder="Background Info (Optional)"
              className="w-full p-1.5 bg-gray-50 border border-gray-300 rounded-md text-xs resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent focus:bg-white transition-colors"
              rows={1}
              style={{ minHeight: '24px', maxHeight: '200px' }}
            />
          </div>

          {/* Query Sections */}
          {querySections.map((section) => {
            const isASREnabled = section.toggles.asr
            const isOtherToggleEnabled = section.toggles.multimodal || section.toggles.ic || section.toggles.ocr

             return (
               <div key={section.id} className="flex flex-col gap-1.5 border-2 border-gray-300 rounded-lg bg-gray-50 shadow-sm p-2 relative">
                 {/* Remove button */}
                 {querySections.length > 1 && (
                   <button
                     onClick={() => removeQuerySection(section.id)}
                     className="absolute -top-2 -right-2 w-5 h-5 flex items-center justify-center bg-white text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors border border-gray-300 shadow-sm z-10"
                     aria-label="Remove query section"
                   >
                     <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                     </svg>
                   </button>
                 )}
                 {/* Query input div */}
                <div>
                  <textarea
                    value={section.query}
                    onChange={(e) => {
                      updateQuerySection(section.id, { query: e.target.value })
                      autoResizeTextarea(e, 150)
                    }}
                    onKeyDown={(e) => handleKeyDown(e, false)}
                    placeholder="Query"
                    className="w-full p-1.5 bg-white border border-gray-300 rounded text-xs resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    rows={1}
                    style={{ minHeight: '32px', maxHeight: '150px' }}
                  />
                </div>

                {/* OCR text input div - between query and object */}
                <div>
                  <textarea
                    value={section.ocrText || ''}
                    onChange={(e) => {
                      updateQuerySection(section.id, { ocrText: e.target.value })
                      autoResizeTextarea(e, 150)
                    }}
                    onKeyDown={(e) => handleKeyDown(e, false)}
                    placeholder="OCR text"
                    disabled={!section.toggles.ocr}
                    className={`w-full p-1.5 bg-white border border-gray-300 rounded text-xs resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent ${
                      !section.toggles.ocr ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''
                    }`}
                    rows={1}
                    style={{ minHeight: '24px', maxHeight: '150px' }}
                  />
                </div>

                {/* Object selection div */}
                <div className="relative flex-shrink-0">
                  <ObjectSelector
                    selectedObjects={section.selectedObjects}
                    onSelectionChange={(objects) => updateQuerySection(section.id, { selectedObjects: objects })}
                    disabled={!section.toggles.objectFilter}
                  />
                </div>

                {/* Toggle buttons div - 6 buttons in 2x3 grid */}
                <div className="grid grid-cols-3 grid-rows-2 gap-1 items-center justify-items-center flex-shrink-0">
                  <ToggleButton
                    label="Multimodal"
                    isOn={section.toggles.multimodal}
                    onToggle={() => handleToggle(section.id, 'multimodal')}
                    disabled={isASREnabled}
                  />
                  <ToggleButton
                    label="IC"
                    isOn={section.toggles.ic}
                    onToggle={() => handleToggle(section.id, 'ic')}
                    disabled={isASREnabled}
                  />
                  <ToggleButton
                    label="ASR"
                    isOn={section.toggles.asr}
                    onToggle={() => handleToggle(section.id, 'asr')}
                    disabled={isOtherToggleEnabled}
                  />
                  <ToggleButton
                    label="OCR"
                    isOn={section.toggles.ocr}
                    onToggle={() => handleToggle(section.id, 'ocr')}
                    disabled={isASREnabled}
                  />
                  <ToggleButton
                    label="Object"
                    isOn={section.toggles.objectFilter}
                    onToggle={() => handleToggle(section.id, 'objectFilter')}
                    disabled={!hasSearched}
                  />
                </div>
              </div>
            )
          })}

          {/* Add Query Button */}
          <button
            onClick={addQuerySection}
            className="w-full py-2 px-4 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
          >
            Add Query
          </button>

          {/* Image Search (upload) */}
          {onImageUploadSearch && (
            <div className="mt-4 border-2 border-gray-300 rounded-lg bg-gray-50 shadow-sm p-3 space-y-2">
              <h3 className="text-xs font-semibold text-gray-700">
                Image Search (upload)
              </h3>
              <p className="text-[10px] text-gray-500 italic">
                💡 Tip: Paste image from clipboard (Ctrl+V / Cmd+V) to search instantly
              </p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => {
                  const file = e.target.files && e.target.files[0]
                  setUploadFile(file || null)
                }}
                className="w-full text-[11px] text-gray-700"
              />
              {uploadFile && (
                <p className="text-[11px] text-gray-500 break-all">
                  Selected: {uploadFile.name} ({(uploadFile.size / 1024).toFixed(1)} KB)
                </p>
              )}
              <button
                type="button"
                onClick={() => {
                  if (uploadFile) {
                    onImageUploadSearch(uploadFile)
                  }
                }}
                disabled={!uploadFile || isSearching}
                className="w-full py-1.5 px-3 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSearching ? 'Searching...' : 'Search by Image'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile overlay - chỉ hiện khi sidebar mở trên mobile */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
})

export default Sidebar

