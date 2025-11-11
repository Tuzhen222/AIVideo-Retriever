import React, { useState, useImperativeHandle, forwardRef } from 'react'
import ToggleButton from '../components/ToggleButton'
import ObjectSelector from '../components/ObjectSelector'

const Sidebar = forwardRef(function Sidebar({ hasSearched, onQuerySectionsChange, onSearch, isSearching = false }, ref) {
  const [isOpen, setIsOpen] = useState(true)
  const [backgroundInfo, setBackgroundInfo] = useState('')
  
  // State for multiple query sections
  const [querySections, setQuerySections] = useState([
    {
      id: 1,
      query: '',
      selectedObjects: [],
      toggles: {
        multimodal: false,
        ic: false,
        asr: false,
        ocr: false,
        genImage: false,
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
        selectedObjects: [],
        toggles: {
          multimodal: false,
          ic: false,
          asr: false,
          ocr: false,
          genImage: false,
          objectFilter: false,
        }
      }])
    },
    getQuerySectionsCount: () => querySections.length,
    getQuerySections: () => querySections,
    getBackgroundInfo: () => backgroundInfo
  }))

  // Notify parent when query sections change
  React.useEffect(() => {
    if (onQuerySectionsChange) {
      onQuerySectionsChange(querySections.length)
    }
  }, [querySections.length, onQuerySectionsChange])

  // Add new query section
  const addQuerySection = () => {
    const newId = Math.max(...querySections.map(s => s.id), 0) + 1
    setQuerySections([...querySections, {
      id: newId,
      query: '',
      selectedObjects: [],
      toggles: {
        multimodal: false,
        ic: false,
        asr: false,
        ocr: false,
        genImage: false,
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
      newToggles.genImage = false
      newToggles.asr = true
    }
    // If any other search method toggle is being turned on (excluding objectFilter)
    else if (key !== 'asr' && key !== 'objectFilter' && !section.toggles[key]) {
      // Turn off ASR (if it was on)
      newToggles.asr = false
      // Allow this toggle to be turned on
      newToggles[key] = true
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
          <div className="border-2 border-gray-300 rounded-lg bg-white shadow-sm p-3">
            <textarea
              value={backgroundInfo}
              onChange={(e) => setBackgroundInfo(e.target.value)}
              onKeyDown={(e) => handleKeyDown(e, true)}
              placeholder="Background Info (Optional)"
              className="w-full p-2 bg-gray-50 border border-gray-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent focus:bg-white transition-colors"
              rows={3}
            />
          </div>

          {/* Query Sections */}
          {querySections.map((section) => {
            const isASREnabled = section.toggles.asr
            const isOtherToggleEnabled = section.toggles.multimodal || section.toggles.ic || section.toggles.ocr || section.toggles.genImage

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
                <div className="h-[50px]">
                  <textarea
                    value={section.query}
                    onChange={(e) => updateQuerySection(section.id, { query: e.target.value })}
                    onKeyDown={(e) => handleKeyDown(e, false)}
                    placeholder="Query"
                    className="w-full h-full p-1.5 bg-white border border-gray-300 rounded text-xs resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                    rows={2}
                  />
                </div>

                {/* Object selection div */}
                <div className="h-8 relative flex-shrink-0">
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
                    label="Gen Img"
                    isOn={section.toggles.genImage}
                    onToggle={() => handleToggle(section.id, 'genImage')}
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
        </div>

        {/* Sidebar content - sẽ thêm sau */}
        <div className="p-4">
          {/* Content sẽ được thêm vào đây */}
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

