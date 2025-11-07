import React from 'react'

function StageButtons({ onStageClick, onTemporalResultClick }) {
  return (
    <div className="md:absolute md:left-[208px]">
      <div className="flex items-center gap-1">
        <button
          onClick={() => onStageClick(1)}
          className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
        >
          Stage 1
        </button>
        <button
          onClick={() => onStageClick(2)}
          className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
        >
          Stage 2
        </button>
        <button
          onClick={() => onStageClick(3)}
          className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
        >
          Stage 3
        </button>
        <button
          onClick={onTemporalResultClick}
          className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
        >
          Temporal Result
        </button>
      </div>
    </div>
  )
}

export default StageButtons

