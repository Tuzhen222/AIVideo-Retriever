// In production (Docker), API is proxied through nginx, so use relative URLs
// In development, use the backend URL directly
// In dev, use relative path so Vite proxy forwards to backend container.
// In prod, optionally honor VITE_API_BASE_URL (e.g., through nginx).
const API_BASE_URL = import.meta.env.DEV
  ? ''
  : (import.meta.env.VITE_API_BASE_URL || '')

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
  async search({ query, method = 'ensemble', top_k = null, filters = null }) {
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
   * Get search configuration (defaults, limits)
   */
  async getSearchConfig() {
    return this.request('/api/search/config')
  }

  /**
   * Get media index (YouTube links)
   */
  async getMediaIndex() {
    return this.request('/api/media-index')
  }

  /**
   * Get FPS mapping
   */
  async getFpsMapping() {
    return this.request('/api/fps-mapping')
  }

  /**
   * Get keyframe mapping (mapping_kf.json) - for OCR and Qdrant search results
   */
  async getMappingKf() {
    return this.request('/api/mapping-kf')
  }

  /**
   * Get scene mapping (mapping_scene.json) - for ASR search results
   */
  async getMappingScene() {
    return this.request('/api/mapping-scene')
  }

  /**
   * Search with multiple queries (for ensemble search)
   * @param {Array} queries - Array of query objects
   * @param {Object} options - Search options
   */
  async searchMultiple(queries, options = {}) {
    const mainQuery = queries[0]?.query || "";
    const method = options.method || "ensemble";  
  
    return this.search({
      query: mainQuery,
      method,
      top_k: options.top_k || null,
      filters: options.filters || null,
    });
  }  
}

// Export singleton instance
export default new ApiService()

