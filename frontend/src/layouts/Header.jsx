import React, { useState, useEffect } from 'react'
import ClearButton from '../components/ClearButton'
import SearchButton from '../components/SearchButton'
import StageButtons from '../components/StageButtons'
import ViewControls from '../components/ViewControls'
import QButtons from '../components/QButtons'

function Header({ onSearch, onClear, hasSearched, querySectionsCount, viewMode, onViewModeChange, isSearching = false, selectedQ: parentSelectedQ, onQChange, selectedStage: parentSelectedStage, onStageChange }) {
  const [selectedQ, setSelectedQ] = useState(parentSelectedQ || 'Q0')
  const [selectedStage, setSelectedStage] = useState(parentSelectedStage || 1)
  const [selectedTemporal, setSelectedTemporal] = useState(false)
  
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
    setSelectedStage(null)
    setSelectedQ('Q0') // Reset về Q0 khi click Temporal Result
  }

  const handleQClick = (q) => {
    setSelectedQ(q)
    console.log(`${q} clicked`)
    if (onQChange) {
      onQChange(q)  // Notify parent
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

        {/* Q Buttons - chỉ hiện khi mode A hoặc M */}
        {(viewMode === 'A' || viewMode === 'M') && (
          <QButtons onQClick={handleQClick} selectedQ={selectedQ} />
        )}
      </div>

      {/* Container bên phải - Controls */}
      <ViewControls viewMode={viewMode} onViewModeChange={onViewModeChange} />
    </div>
  )
}

export default Header

