import axios, { type AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'

interface ApiErrorResponse {
  detail?: string | Record<string, unknown>
  message?: string
}

/**
 * Custom error class that preserves structured error details from the API.
 *
 * When the backend returns a structured detail object (e.g. for CSV schema
 * validation errors), this lets the UI inspect `error.detail` to render
 * a rich error panel instead of just showing a flat string.
 */
export class ApiError extends Error {
  detail: Record<string, unknown> | null

  constructor(message: string, detail: Record<string, unknown> | null = null) {
    super(message)
    this.name = 'ApiError'
    this.detail = detail
  }
}

// All requests go through Vite's proxy → localhost:8000
// In production, replace baseURL with your deployed API URL
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor — normalize errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail

    // Structured error (e.g. INVALID_CSV_SCHEMA) — preserve the full object
    if (detail && typeof detail === 'object') {
      const title = detail.title || 'Request failed'
      return Promise.reject(new ApiError(String(title), detail))
    }

    // Plain string error
    const message =
      (typeof detail === 'string' ? detail : null) ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'
    return Promise.reject(new ApiError(message))
  }
)

export default apiClient