import React, { useState } from 'react'

function Sidebar() {
  const [isOpen, setIsOpen] = useState(true)

  return (
    <>
      {/* Mobile toggle button - chỉ hiện trên mobile */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed top-16 left-0 z-50 bg-red-500 text-white p-2 rounded-r-lg shadow-lg"
        aria-label="Toggle sidebar"
      >
        {isOpen ? '◀' : '▶'}
      </button>

      {/* Sidebar */}
      <div
        className={`
          bg-white border-r border-gray-200
          transition-all duration-300 ease-in-out
          h-full overflow-y-auto
          w-52
          md:relative md:block
          ${isOpen ? 'fixed inset-y-0 left-0 top-0 z-40 block' : 'hidden md:block'}
        `}
      >
        {/* Sidebar content - sẽ thêm sau */}
        <div className="p-4">
          {/* Content sẽ được thêm vào đây */}
        </div>
      </div>

      {/* Mobile overlay - chỉ hiện khi sidebar mở trên mobile */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}

export default Sidebar

