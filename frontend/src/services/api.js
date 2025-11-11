// In production (Docker), API is proxied through nginx, so use relative URLs
// In development, use the backend URL directly
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (import.meta.env.PROD ? '' : 'http://localhost:8000')

/**
 * API service for backend communication
 */
class ApiService {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL
  }

  /**
   * Make API request
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(error.detail || `HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  /**
   * Health check
   */
  async healthCheck() {
    return this.request('/health')
  }

  /**
   * Search videos
   * @param {Object} searchParams - Search parameters
   * @param {string} searchParams.query - Search query
   * @param {string} searchParams.method - Search method (ensemble, clip, beit3, etc.)
   * @param {number} searchParams.top_k - Number of results
   * @param {Object} searchParams.filters - Additional filters
   */
  async search({ query, method = 'ensemble', top_k = 10, filters = null }) {
    return this.request('/api/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        method,
        top_k,
        filters,
      }),
    })
  }

  /**
   * Get available search methods
   */
  async getSearchMethods() {
    return this.request('/api/search/methods')
  }

  /**
   * Search with multiple queries (for ensemble search)
   * @param {Array} queries - Array of query objects
   * @param {Object} options - Search options
   */
  async searchMultiple(queries, options = {}) {
    // For now, combine queries or use first query
    // This can be extended based on backend API
    const mainQuery = queries.length > 0 ? queries[0].query : ''
    const method = queries[0]?.method || options.method || 'ensemble'
    
    // Build filters from query sections
    const filters = {
      queries: queries.map(q => ({
        query: q.query,
        toggles: q.toggles,
        selectedObjects: q.selectedObjects,
      })),
      ...options,
    }

    return this.search({
      query: mainQuery,
      method,
      top_k: options.top_k || 10,
      filters,
    })
  }
}

// Export singleton instance
export default new ApiService()

