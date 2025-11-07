import React from 'react'

function StageButtons({ onStageClick, onTemporalResultClick, hasSearched, querySectionsCount, selectedStage, selectedTemporal }) {
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
    <div className="flex items-center gap-1">
        <button
          onClick={() => onStageClick(1)}
          className={`px-2 h-full rounded text-xs font-medium transition-colors flex items-center ${
            selectedStage === 1
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-gray-300 hover:bg-gray-400 text-gray-800'
          }`}
        >
          Stage 1
        </button>
        {Array.from({ length: additionalStagesCount }, (_, i) => i + 2).map((stageNum) => (
          <button
            key={stageNum}
            onClick={() => onStageClick(stageNum)}
            className={`px-2 h-full rounded text-xs font-medium transition-colors flex items-center ${
              selectedStage === stageNum
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-gray-300 hover:bg-gray-400 text-gray-800'
            }`}
          >
            Stage {stageNum}
          </button>
        ))}
        {showTemporalResult && (
          <button
            onClick={onTemporalResultClick}
            className={`px-2 h-full rounded text-xs font-medium transition-colors flex items-center ${
              selectedTemporal
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-gray-300 hover:bg-gray-400 text-gray-800'
            }`}
          >
            Temporal Result
          </button>
        )}
      </div>
  )
}

export default StageButtons

