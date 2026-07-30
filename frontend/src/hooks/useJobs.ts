import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { jobsApi } from '@/api/jobs'
import type { JobStatus } from '@/types'

// Query keys — centralized to avoid string typos
export const queryKeys = {
  health: ['health'] as const,
  jobs: (status?: string) => ['jobs', status] as const,
  jobStatus: (id: string) => ['job', id, 'status'] as const,
  jobResults: (id: string) => ['job', id, 'results'] as const,
}

// Health check — polls every 30s
export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: jobsApi.health,
    refetchInterval: 30_000,
  })
}

// All jobs list
export function useJobs(status?: string) {
  return useQuery({
    queryKey: queryKeys.jobs(status),
    queryFn: () => jobsApi.list(status),
    refetchInterval: 10_000,
  })
}

// Single job status with conditional polling
// Polls every 2s while pending/processing, stops when completed/failed
export function useJobStatus(jobId: string | null) {
  return useQuery({
    queryKey: queryKeys.jobStatus(jobId!),
    queryFn: () => jobsApi.getStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status as JobStatus | undefined
      if (!status) return 2_000
      return status === 'completed' || status === 'failed' ? false : 2_000
    },
  })
}

// Job results — only fetches when job is completed
export function useJobResults(jobId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.jobResults(jobId!),
    queryFn: () => jobsApi.getResults(jobId!),
    enabled: !!jobId && enabled,
  })
}

// Upload mutation
export function useUploadJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: jobsApi.upload,
    onSuccess: () => {
      // Invalidate jobs list so it refreshes after upload
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}