import React, { useState, useRef, useEffect } from 'react'

// Common objects list - can be replaced with API call later
const AVAILABLE_OBJECTS = [
  'car', 'helmet', 'person', 'bicycle', 'motorcycle', 'bus', 'truck',
  'dog', 'cat', 'bird', 'horse', 'cow', 'sheep',
  'chair', 'table', 'sofa', 'bed', 'laptop', 'phone', 'book',
  'bottle', 'cup', 'bowl', 'fork', 'knife', 'spoon',
  'traffic light', 'stop sign', 'parking meter', 'bench',
  'umbrella', 'handbag', 'backpack', 'suitcase',
  'sports ball', 'kite', 'baseball bat', 'skateboard',
  'surfboard', 'tennis racket', 'bottle', 'wine glass'
]

function ObjectSelector({ selectedObjects, onSelectionChange, disabled = false }) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredObjects, setFilteredObjects] = useState(AVAILABLE_OBJECTS)
  const containerRef = useRef(null)
  const inputRef = useRef(null)

  // Filter objects based on search term
  useEffect(() => {
    if (searchTerm.trim() === '') {
      setFilteredObjects(AVAILABLE_OBJECTS.filter(obj => !selectedObjects.includes(obj)))
    } else {
      const filtered = AVAILABLE_OBJECTS.filter(obj => 
        obj.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !selectedObjects.includes(obj)
      )
      setFilteredObjects(filtered)
    }
  }, [searchTerm, selectedObjects])

  // Close dropdown when clicking outside or when disabled
  useEffect(() => {
    if (disabled) {
      setIsOpen(false)
      setSearchTerm('')
    }
  }, [disabled])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false)
        setSearchTerm('')
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleInputClick = () => {
    if (disabled) return
    setIsOpen(true)
    setTimeout(() => {
      inputRef.current?.focus()
    }, 0)
  }

  const handleObjectSelect = (object) => {
    if (!selectedObjects.includes(object)) {
      onSelectionChange([...selectedObjects, object])
    }
    setSearchTerm('')
    setIsOpen(false)
  }

  const handleRemoveObject = (object, e) => {
    e.stopPropagation()
    onSelectionChange(selectedObjects.filter(obj => obj !== object))
  }

  const displayText = selectedObjects.length > 0 
    ? selectedObjects.join(', ') + (selectedObjects.length < AVAILABLE_OBJECTS.length ? ', ..' : '')
    : 'No objects selected'

  return (
    <div ref={containerRef} className="relative w-full h-full">
      {/* Input field */}
      <div
        onClick={handleInputClick}
        className={`w-full h-full p-1 bg-white border border-gray-300 rounded text-xs text-gray-600 flex items-center ${
          disabled ? 'cursor-not-allowed opacity-50 bg-gray-100' : 'cursor-text'
        } ${
          isOpen ? 'ring-2 ring-red-500 border-transparent' : ''
        }`}
      >
        {selectedObjects.length > 0 && !isOpen && (
          <div className="flex flex-wrap gap-1 flex-1 items-center">
            {selectedObjects.slice(0, 2).map((obj) => (
              <span
                key={obj}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs"
              >
                {obj}
                <button
                  onClick={(e) => handleRemoveObject(obj, e)}
                  className="hover:text-red-900 focus:outline-none"
                  aria-label={`Remove ${obj}`}
                >
                  ×
                </button>
              </span>
            ))}
            {selectedObjects.length > 2 && (
              <span className="text-gray-600 text-xs">
                +{selectedObjects.length - 2} more
              </span>
            )}
          </div>
        )}
        {selectedObjects.length === 0 && !isOpen && (
          <span className="text-gray-400">{displayText}</span>
        )}
        {isOpen && (
          <input
            ref={inputRef}
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Type to search objects..."
            className="flex-1 outline-none text-gray-700 bg-transparent"
            onClick={(e) => e.stopPropagation()}
          />
        )}
      </div>

      {/* Dropdown list */}
      {isOpen && (
        <div className="absolute top-full left-0 z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {filteredObjects.length > 0 ? (
            <ul className="py-1">
              {filteredObjects.map((object) => (
                <li
                  key={object}
                  onClick={() => handleObjectSelect(object)}
                  className="px-3 py-2 hover:bg-red-50 cursor-pointer text-sm text-gray-700 flex items-center"
                >
                  {object}
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-3 py-2 text-sm text-gray-500 text-center">
              {searchTerm ? 'No objects found' : 'All objects selected'}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ObjectSelector

