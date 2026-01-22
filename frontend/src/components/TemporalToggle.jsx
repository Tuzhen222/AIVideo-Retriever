import React from 'react'

/**
 * Toggle button for switching temporal aggregation mode
 * - Default (off): ID aggregation mode
 * - Active (on): Tuple sequence mode
 */
function TemporalToggle({ isActive, onClick, disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        px-2 py-0.5 rounded text-xs font-medium transition-all h-5 flex items-center
        ${disabled 
          ? 'opacity-50 cursor-not-allowed bg-gray-200 text-gray-500' 
          : isActive
            ? 'bg-red-600 text-white hover:bg-red-700'
            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
        }
      `}
      title={isActive 
        ? 'Temporal Tuple Mode: Showing sequences with increasing frames' 
        : 'Temporal ID Mode: Aggregated by media ID (click to switch to Tuple Mode)'
      }
    >
      {isActive ? (
        <span className="flex items-center gap-1">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          Tuple View
        </span>
      ) : (
        <span className="flex items-center gap-1">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          ID View
        </span>
      )}
    </button>
  )
}

export default TemporalToggle
