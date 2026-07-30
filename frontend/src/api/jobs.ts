import apiClient from './client'
import type {
  UploadResponse,
  Job,
  JobListResponse,
  JobResults,
  HealthResponse,
} from '@/types'

export const jobsApi = {
  // Upload CSV file
  upload: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await apiClient.post<UploadResponse>('/jobs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  // Get job status (used for polling)
  getStatus: async (jobId: string): Promise<Job> => {
    const { data } = await apiClient.get<Job>(`/jobs/${jobId}/status`)
    return data
  },

  // Get full results
  getResults: async (jobId: string): Promise<JobResults> => {
    const { data } = await apiClient.get<JobResults>(`/jobs/${jobId}/results`)
    return data
  },

  // List all jobs
  list: async (status?: string): Promise<JobListResponse> => {
    const params = status ? { status } : {}
    const { data } = await apiClient.get<JobListResponse>('/jobs', { params })
    return data
  },

  // Health check
  health: async (): Promise<HealthResponse> => {
    const { data } = await apiClient.get<HealthResponse>('/health')
    return data
  },
}