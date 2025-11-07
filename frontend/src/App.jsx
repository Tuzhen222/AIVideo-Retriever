import React, { useState, useRef } from 'react'
import Header from './layouts/Header'
import Sidebar from './layouts/Sidebar'
import MainContent from './layouts/MainContent'

function App() {
  const [hasSearched, setHasSearched] = useState(false)
  const [searchResults, setSearchResults] = useState(null)
  const [querySectionsCount, setQuerySectionsCount] = useState(1)
  const sidebarRef = useRef(null)

  const handleClear = () => {
    // Reset search state
    setHasSearched(false)
    // Clear search results
    setSearchResults(null)
    // Reset sidebar (query, objects, toggles)
    if (sidebarRef.current) {
      sidebarRef.current.reset()
      setQuerySectionsCount(1)
    }
  }

  const handleSearch = () => {
    setHasSearched(true)
    // Update query sections count
    if (sidebarRef.current) {
      setQuerySectionsCount(sidebarRef.current.getQuerySectionsCount())
    }
    // TODO: Perform search and set searchResults
    // setSearchResults(searchResultsData)
  }

  const handleQuerySectionsChange = (count) => {
    setQuerySectionsCount(count)
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-gray-50">
      {/* Header - Red bar */}
      <Header 
        onSearch={handleSearch} 
        onClear={handleClear}
        hasSearched={hasSearched}
        querySectionsCount={querySectionsCount}
      />
      
      {/* Main layout with sidebar and content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar 
          ref={sidebarRef} 
          hasSearched={hasSearched}
          onQuerySectionsChange={handleQuerySectionsChange}
        />
        
        {/* Main content area */}
        <MainContent searchResults={searchResults} />
      </div>
    </div>
  )
}

export default App

