import React from 'react'
import ClearButton from '../components/ClearButton'
import StageButtons from '../components/StageButtons'
import ViewControls from '../components/ViewControls'

function Header() {
  const handleClear = () => {
    // Clear logic sẽ được thêm sau
    console.log('Clear clicked')
  }

  const handleStage = (stage) => {
    // Stage logic sẽ được thêm sau
    console.log(`Stage ${stage} clicked`)
  }

  const handleTemporalResult = () => {
    // Temporal Result logic sẽ được thêm sau
    console.log('Temporal Result clicked')
  }

  return (
    <div className="w-full bg-red-400 px-3 py-1 flex items-center gap-2 h-6 relative">
      {/* Clear Button - bên trái */}
      <ClearButton onClick={handleClear} />

      {/* Stage buttons container - căn chỉnh ngay đường biên sidebar */}
      {/* w-52 = 208px, absolute left tính từ mép trái header container (không phải content area) */}
      {/* Vậy left = 208px để căn với mép phải sidebar */}
      <StageButtons 
        onStageClick={handleStage} 
        onTemporalResultClick={handleTemporalResult}
      />

      {/* Container bên phải - Controls */}
      <ViewControls />
    </div>
  )
}

export default Header

