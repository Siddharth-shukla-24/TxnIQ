import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUploadJob, useJobStatus } from '@/hooks/useJobs'
import { ApiError } from '@/api/client'
import StatusBadge from '@/components/StatusBadge'
import {
  Upload,
  FileText,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  ArrowRight,
  Download,
} from 'lucide-react'
import clsx from 'clsx'
import type { JobStatus } from '@/types'

type UploadState = 'idle' | 'uploading' | 'polling' | 'done' | 'error'

/** Structured error detail from the API (e.g. INVALID_CSV_SCHEMA) */
interface CsvSchemaError {
  error_code: string
  title: string
  description: string
  required_columns: string[]
  missing_columns: string[]
}

const PIPELINE_STAGES = [
  { key: 'pending', label: 'Job Queued', description: 'Task dispatched via Redis broker' },
  { key: 'processing', label: 'Pipeline Running', description: 'Cleaning → Anomaly detection → LLM → Summary' },
  { key: 'completed', label: 'Complete', description: 'Results persisted to PostgreSQL' },
]

export default function UploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [schemaError, setSchemaError] = useState<CsvSchemaError | null>(null)

  const uploadMutation = useUploadJob()
  const { data: jobStatus } = useJobStatus(uploadState === 'polling' ? jobId : null)

  const currentStatus = jobStatus?.status
  if (uploadState === 'polling' && currentStatus === 'completed') setUploadState('done')
  if (uploadState === 'polling' && currentStatus === 'failed') {
    setUploadState('error')
    setErrorMessage(jobStatus?.error_message ?? 'Job failed during processing')
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped?.name.endsWith('.csv')) setFile(dropped)
  }, [])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) setFile(selected)
  }

  const handleUpload = async () => {
    if (!file) return
    setUploadState('uploading')
    setErrorMessage(null)
    setSchemaError(null)
    try {
      const result = await uploadMutation.mutateAsync(file)
      setJobId(result.job_id)
      setUploadState('polling')
    } catch (err) {
      setUploadState('error')

      // Check for structured CSV schema error
      if (err instanceof ApiError && err.detail?.error_code === 'INVALID_CSV_SCHEMA') {
        setSchemaError(err.detail as unknown as CsvSchemaError)
        setErrorMessage(null)
      } else {
        setErrorMessage(err instanceof Error ? err.message : 'Upload failed')
        setSchemaError(null)
      }
    }
  }

  const reset = () => {
    setFile(null)
    setJobId(null)
    setUploadState('idle')
    setErrorMessage(null)
    setSchemaError(null)
  }

  return (
    <div className="max-w-xl mx-auto animate-fade-in">
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-white tracking-tight">Upload CSV</h2>
        <p className="text-sm text-[#555] mt-0.5">
          Run the full AI processing pipeline on your transaction data
        </p>
      </div>

      {/* Drop zone */}
      {uploadState === 'idle' && (
        <>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={clsx(
              'input-file-zone',
              dragOver && 'input-file-zone-active'
            )}
          >
            <input
              type="file"
              accept=".csv"
              onChange={onFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="icon-box-lg bg-white/[0.04] border border-white/[0.06] mx-auto mb-4">
              <Upload className="w-5 h-5 text-[#555]" />
            </div>
            <p className="text-sm font-medium text-[#ccc]">
              Drop your CSV here
            </p>
            <p className="text-xs text-[#444] mt-1">
              or click to browse · .csv · max 10 MB
            </p>
          </div>

          {file && (
            <div className="mt-3 flex items-center gap-3 px-4 py-3.5 bg-white/[0.03] border border-[#1f1f1f] rounded-xl animate-slide-up">
              <div className="icon-box-md bg-blue-500/10 border border-blue-500/20">
                <FileText className="w-4 h-4 text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{file.name}</p>
                <p className="text-xs text-[#555]">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
              <button
                onClick={() => setFile(null)}
                className="text-[#444] hover:text-[#888] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {file && (
            <button onClick={handleUpload} className="btn-primary w-full mt-4">
              <Upload className="w-4 h-4" />
              Start Processing
            </button>
          )}
        </>
      )}

      {/* Uploading */}
      {uploadState === 'uploading' && (
        <div className="card flex items-center gap-3 animate-fade-in">
          <Loader2 className="w-4 h-4 text-blue-400 animate-spin flex-shrink-0" />
          <p className="text-sm text-[#888]">Uploading and validating CSV…</p>
        </div>
      )}

      {/* Pipeline progress */}
      {(uploadState === 'polling' || uploadState === 'done') && jobStatus && (
        <div className="card animate-slide-up">
          <div className="flex items-center justify-between mb-6">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{file?.name}</p>
              <p className="text-[11px] text-[#444] font-mono mt-0.5">
                {jobId?.slice(0, 8)}…
              </p>
            </div>
            <StatusBadge status={jobStatus.status as JobStatus} />
          </div>

          {/* Stages */}
          <div className="space-y-1">
            {PIPELINE_STAGES.map((stage, idx) => {
              const order = ['pending', 'processing', 'completed']
              const currentIdx = order.indexOf(jobStatus.status)
              const stageIdx = order.indexOf(stage.key)
              const isDone = stageIdx < currentIdx || jobStatus.status === 'completed'
              const isActive = stageIdx === currentIdx && jobStatus.status !== 'completed'

              return (
                <div key={stage.key} className="flex items-start gap-4">
                  <div className="flex flex-col items-center pt-0.5">
                    <div
                      className={clsx(
                        'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-colors',
                        isDone && 'bg-emerald-500/20 text-emerald-400',
                        isActive && 'bg-blue-500/20 text-blue-400',
                        !isDone && !isActive && 'bg-white/[0.04] text-[#444]'
                      )}
                    >
                      {isDone ? (
                        <CheckCircle className="w-3.5 h-3.5" />
                      ) : isActive ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        idx + 1
                      )}
                    </div>
                    {idx < PIPELINE_STAGES.length - 1 && (
                      <div
                        className={clsx(
                          'w-px h-8 mt-1 transition-colors',
                          isDone ? 'bg-emerald-500/20' : 'bg-[#1a1a1a]'
                        )}
                      />
                    )}
                  </div>
                  <div className="pb-4">
                    <p
                      className={clsx(
                        'text-sm font-medium transition-colors',
                        isDone || isActive ? 'text-white' : 'text-[#444]'
                      )}
                    >
                      {stage.label}
                    </p>
                    <p className="text-xs text-[#555] mt-0.5">{stage.description}</p>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Row counts */}
          {jobStatus.row_count_raw != null && (
            <div className="mt-5 pt-5 border-t border-[#1a1a1a] grid grid-cols-2 gap-4">
              <div>
                <p className="section-label">Raw rows</p>
                <p className="text-2xl font-bold text-white font-mono mt-1">
                  {jobStatus.row_count_raw}
                </p>
              </div>
              {jobStatus.row_count_clean != null && (
                <div>
                  <p className="section-label">After cleaning</p>
                  <p className="text-2xl font-bold text-emerald-400 font-mono mt-1">
                    {jobStatus.row_count_clean}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Done CTA */}
      {uploadState === 'done' && jobId && (
        <div className="mt-4 flex gap-3 animate-slide-up">
          <button
            onClick={() => navigate(`/jobs/${jobId}`)}
            className="btn-primary flex-1"
          >
            View Results <ArrowRight className="w-4 h-4" />
          </button>
          <button onClick={reset} className="btn-secondary px-5">
            Upload Another
          </button>
        </div>
      )}

      {/* Error — Structured CSV Schema Error */}
      {uploadState === 'error' && schemaError && (
        <div className="mt-4 space-y-3 animate-slide-up">
          <div className="px-5 py-5 bg-red-500/[0.04] border border-red-500/15 rounded-2xl">
            {/* Header */}
            <div className="flex items-start gap-3 mb-4">
              <div className="icon-box-md bg-red-500/10 border border-red-500/20 mt-0.5">
                <AlertCircle className="w-[18px] h-[18px] text-red-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-red-400">{schemaError.title}</p>
                <p className="text-xs text-[#888] mt-1 leading-relaxed">
                  {schemaError.description}
                </p>
              </div>
            </div>

            {/* Required columns */}
            <div className="mt-4 pt-4 border-t border-red-500/10">
              <p className="section-label mb-3">
                Required Columns
              </p>
              <div className="grid grid-cols-3 gap-1.5">
                {schemaError.required_columns.map((col) => {
                  const isMissing = schemaError.missing_columns.includes(col)
                  return (
                    <div
                      key={col}
                      className={clsx(
                        'px-2.5 py-1.5 rounded-lg text-xs font-mono text-center transition-colors',
                        isMissing
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                          : 'bg-white/[0.03] text-[#666] border border-white/[0.05]'
                      )}
                    >
                      {col}
                      {isMissing && <span className="ml-1 text-red-500">✕</span>}
                    </div>
                  )
                })}
              </div>
              {schemaError.missing_columns.length > 0 && (
                <p className="text-[11px] text-[#555] mt-2.5">
                  <span className="text-red-400/70">✕</span>{' '}
                  {schemaError.missing_columns.length === 1 ? '1 column is' : `${schemaError.missing_columns.length} columns are`} missing from your file
                </p>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button onClick={reset} className="btn-secondary flex-1">
              Try Again
            </button>
            <a
              href="/api/jobs/sample-csv"
              download
              className="btn-secondary flex-1 flex items-center justify-center gap-2 no-underline"
            >
              <Download className="w-3.5 h-3.5" />
              Download Sample CSV
            </a>
          </div>
        </div>
      )}

      {/* Error — Generic fallback */}
      {uploadState === 'error' && !schemaError && (
        <div className="mt-4 space-y-3 animate-slide-up">
          <div className="alert-error">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-400">Processing failed</p>
              <p className="text-xs text-[#666] mt-0.5">{errorMessage}</p>
            </div>
          </div>
          <button onClick={reset} className="btn-secondary w-full">
            Try Again
          </button>
        </div>
      )}
    </div>
  )
}