import React from 'react'

function ToggleButton({ label, isOn, onToggle, disabled = false }) {
  return (
    <div className="flex flex-col items-center justify-center gap-0.5">
      <button
        onClick={disabled ? undefined : onToggle}
        disabled={disabled}
        className={`
          relative w-9 h-4 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1
          ${isOn ? 'bg-red-600' : 'bg-gray-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        aria-label={`Toggle ${label}`}
      >
        <span
          className={`
            absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 shadow-sm
            ${isOn ? 'translate-x-[1rem]' : 'translate-x-0'}
          `}
        />
      </button>
      <span className={`text-[10px] leading-tight text-center whitespace-nowrap ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>{label}</span>
    </div>
  )
}

export default ToggleButton

