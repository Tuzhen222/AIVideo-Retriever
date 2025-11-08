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

      {/* Input Num */}
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={numValue}
          onChange={(e) => {
            const value = e.target.value
            // Chỉ cho phép số dương hoặc rỗng
            if (value === '' || (parseInt(value) >= 0 && !isNaN(parseInt(value)))) {
              setNumValue(value)
            }
          }}
          placeholder="Num"
          min="0"
          className="w-16 px-2 py-0.5 rounded border border-gray-300 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-white"
          title="Number of Advanced Temporal Search"
        />
      </div>

      {/* Toggle Switch */}
      <button
        onClick={() => setToggleState(!toggleState)}
        className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
          toggleState ? 'bg-blue-500' : 'bg-gray-300'
        }`}
        aria-label="Toggle"
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-md transform transition-transform duration-200 ${
            toggleState ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )
}

export default ViewControls

