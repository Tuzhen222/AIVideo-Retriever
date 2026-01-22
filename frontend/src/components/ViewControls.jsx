import React, { useState } from 'react'

function ViewControls({ viewMode, onViewModeChange }) {
  const [numValue, setNumValue] = useState('10')
  const [toggleState, setToggleState] = useState(false)

  const handleViewModeClick = () => {
    // Chuyển đổi giữa E -> A -> M -> E
    const modes = ['E', 'A', 'M']
    const currentIndex = modes.indexOf(viewMode || 'E')
    const newMode = modes[(currentIndex + 1) % modes.length]
    if (onViewModeChange) {
      onViewModeChange(newMode)
    }
  }

  return (
    <div className="ml-auto flex items-center gap-2">
      {/* Nút tròn đổi mode E/A/M */}
      <button
        onClick={handleViewModeClick}
        className="w-6 h-6 rounded-full bg-white hover:bg-gray-200 active:bg-gray-300 border border-gray-300 flex items-center justify-center text-xs font-medium text-gray-800 transition-colors duration-200 shadow-sm"
        title="View Mode: E=Ensemble, A=Augment Query, M=Method"
      >
        {viewMode || 'E'}
      </button>
    </div>
  )
}

export default ViewControls

