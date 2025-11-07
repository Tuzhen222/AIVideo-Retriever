import React from 'react'

function StageButtons({ onStageClick, onTemporalResultClick, hasSearched, querySectionsCount }) {
  // Show Stage 1 if searched
  const showStage1 = hasSearched
  // Show additional stages based on query sections count
  // If 2 sections → Stage 2, if 3 sections → Stage 2 & 3, if 4 sections → Stage 2, 3, 4, etc.
  const additionalStagesCount = querySectionsCount > 1 ? querySectionsCount - 1 : 0
  // Show Temporal Result if 2+ query sections
  const showTemporalResult = querySectionsCount >= 2

  if (!showStage1) {
    return null
  }

  return (
    <div className="md:absolute md:left-[208px]">
      <div className="flex items-center gap-1">
        <button
          onClick={() => onStageClick(1)}
          className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
        >
          Stage 1
        </button>
        {Array.from({ length: additionalStagesCount }, (_, i) => i + 2).map((stageNum) => (
          <button
            key={stageNum}
            onClick={() => onStageClick(stageNum)}
            className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
          >
            Stage {stageNum}
          </button>
        ))}
        {showTemporalResult && (
          <button
            onClick={onTemporalResultClick}
            className="px-2 h-full bg-gray-300 hover:bg-gray-400 text-gray-800 rounded text-xs font-medium transition-colors flex items-center"
          >
            Temporal Result
          </button>
        )}
      </div>
    </div>
  )
}

export default StageButtons

