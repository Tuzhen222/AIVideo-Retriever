import React, { useState } from 'react'

function ViewControls() {
  const [viewMode, setViewMode] = useState('E') // E: Ensemble, A: Augment, M: Method
  const [numValue, setNumValue] = useState('')
  const [toggleState, setToggleState] = useState(false)

  const handleViewModeClick = () => {
    // Chuyển đổi giữa E -> A -> M -> E
    const modes = ['E', 'A', 'M']
    const currentIndex = modes.indexOf(viewMode)
    setViewMode(modes[(currentIndex + 1) % modes.length])
  }

  return (
    <div className="ml-auto flex items-center gap-2">
      {/* Nút tròn đổi mode E/A/M */}
      <button
        onClick={handleViewModeClick}
        className="w-6 h-6 rounded-full bg-white hover:bg-gray-100 border border-gray-300 flex items-center justify-center text-xs font-medium text-gray-800 transition-colors shadow-sm"
        title="View Mode: E=Ensemble, A=Augment Query, M=Method"
      >
        {viewMode}
      </button>

      {/* Input Num */}
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={numValue}
          onChange={(e) => setNumValue(e.target.value)}
          placeholder="Num"
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

