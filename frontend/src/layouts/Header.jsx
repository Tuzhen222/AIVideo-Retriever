import React, { useState, useEffect } from 'react'
import ClearButton from '../components/ClearButton'
import SearchButton from '../components/SearchButton'
import StageButtons from '../components/StageButtons'
import ViewControls from '../components/ViewControls'
import QButtons from '../components/QButtons'
import TemporalToggle from '../components/TemporalToggle'

function Header({ onSearch, onClear, hasSearched, querySectionsCount, viewMode, onViewModeChange, isSearching = false, selectedQ: parentSelectedQ, onQChange, selectedStage: parentSelectedStage, onStageChange, temporalMode: parentTemporalMode, onTemporalModeChange, useAugmented, onAugmentedChange }) {
  const [selectedQ, setSelectedQ] = useState(parentSelectedQ || 'Q0')
  const [selectedStage, setSelectedStage] = useState(parentSelectedStage || 1)
  const [selectedTemporal, setSelectedTemporal] = useState(false)
  const [temporalMode, setTemporalMode] = useState(parentTemporalMode || 'id')
  
  // Sync with parent selectedQ
  useEffect(() => {
    if (parentSelectedQ !== undefined) {
      setSelectedQ(parentSelectedQ)
    }
  }, [parentSelectedQ])

  // Sync with parent selectedStage
  useEffect(() => {
    if (parentSelectedStage !== undefined) {
      setSelectedStage(parentSelectedStage)
    }
  }, [parentSelectedStage])

  // Sync with parent temporalMode
  useEffect(() => {
    if (parentTemporalMode !== undefined) {
      setTemporalMode(parentTemporalMode)
    }
  }, [parentTemporalMode])
  const handleClear = () => {
    // Clear logic sẽ được thêm sau
    console.log('Clear clicked')
    setSelectedStage(1)
    setSelectedTemporal(false)
    setSelectedQ('Q0')
    if (onClear) {
      onClear()
    }
  }

  const handleSearch = () => {
    // Search logic sẽ được thêm sau
    console.log('Search clicked')
    if (onSearch) {
      onSearch()
    }
  }

  const handleStage = (stage) => {
    // Stage logic sẽ được thêm sau
    console.log(`Stage ${stage} clicked`)
    setSelectedStage(stage)
    setSelectedTemporal(false)
    setSelectedQ('Q0') // Reset về Q0 khi đổi stage
    if (onStageChange) {
      onStageChange(stage)  // Notify parent
    }
  }

  const handleTemporalResult = () => {
    // Temporal Result logic sẽ được thêm sau
    console.log('Temporal Result clicked')
    setSelectedTemporal(true)
    setSelectedStage('temporal')  // Set to 'temporal' string
    setSelectedQ('Q0') // Reset về Q0 khi click Temporal Result
    if (onStageChange) {
      onStageChange('temporal')  // Notify parent with 'temporal'
    }
  }

  const handleQClick = (q) => {
    setSelectedQ(q)
    console.log(`${q} clicked`)
    if (onQChange) {
      onQChange(q)  // Notify parent
    }
  }

  const handleTemporalToggle = () => {
    const newMode = temporalMode === 'id' ? 'tuple' : 'id'
    setTemporalMode(newMode)
    console.log(`Temporal mode switched to: ${newMode}`)
    if (onTemporalModeChange) {
      onTemporalModeChange(newMode)
    }
  }

  return (
    <div className="fixed top-0 left-0 right-0 bg-red-400 px-3 py-1 flex items-center gap-2 h-6 z-50">
      {/* Buttons container - Clear and Search */}
      <div className="flex items-center gap-2">
        <ClearButton onClick={handleClear} disabled={isSearching} />
        <SearchButton onClick={handleSearch} isSearching={isSearching} />
      </div>

      {/* Stage buttons và Q buttons container */}
      <div className="md:absolute md:left-[208px] flex items-center gap-3">
        <StageButtons 
          onStageClick={handleStage} 
          onTemporalResultClick={handleTemporalResult}
          hasSearched={hasSearched}
          querySectionsCount={querySectionsCount}
          selectedStage={selectedStage}
          selectedTemporal={selectedTemporal}
        />

        {/* Q Buttons - chỉ hiện khi mode A hoặc M và KHÔNG phải temporal stage */}
        {(viewMode === 'A' || viewMode === 'M') && !selectedTemporal && (
          <QButtons onQClick={handleQClick} selectedQ={selectedQ} />
        )}
      </div>

      {/* Container bên phải - Controls */}
      <div className="ml-auto flex items-center gap-2">
        {/* Temporal toggle - only show when multistage search */}
        {querySectionsCount > 1 && hasSearched && selectedTemporal && (
          <TemporalToggle 
            isActive={temporalMode === 'tuple'}
            onClick={handleTemporalToggle}
            disabled={isSearching}
          />
        )}
        
        {/* Augment toggle button */}
        <button
          onClick={() => onAugmentedChange && onAugmentedChange(!useAugmented)}
          className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors duration-200 shadow-sm ${
            useAugmented 
              ? 'bg-green-600 text-white hover:bg-green-700' 
              : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
          }`}
          title="Query Augmentation (Gemini Q1, Q2)"
        >
          Aug
        </button>
        
        <ViewControls viewMode={viewMode} onViewModeChange={onViewModeChange} />
      </div>
    </div>
  )
}

export default Header

