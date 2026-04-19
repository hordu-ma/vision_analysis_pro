export interface DetectionBox {
  label: string
  confidence: number
  bbox: [number, number, number, number] // [x1, y1, x2, y2]
}

export interface InferenceResponse {
  filename: string
  detections: DetectionBox[]
  metadata: {
    inference_time_ms?: number
    model_version?: string
    engine?: string
    request_id?: string
    detection_count?: number
  }
  visualization?: string
}

export interface BatchInferenceResponse {
  files: InferenceResponse[]
  metadata: {
    request_id?: string
    engine?: string
    file_count?: number
    total_detections?: number
    batch_inference_time_ms?: number
  }
}

export interface InferenceTaskResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'partial_failed'
  created_at: number
  updated_at: number
  file_count: number
  completed_files: number
  progress: number
  results: InferenceResponse[]
  metadata: {
    request_id?: string
    engine?: string
    file_count?: number
    total_detections?: number
    batch_inference_time_ms?: number
    successful_files?: number
    failed_files?: number
    visualize?: boolean
    source_task_id?: string
    replay_mode?: 'retry' | 'rerun' | 'retry_failed'
  }
  error?: {
    code: string
    message: string
    detail?: string
  } | null
}

export interface InferenceTaskFileResult {
  filename: string
  status: 'completed' | 'failed'
  result?: InferenceResponse | null
  error?: {
    code: string
    message: string
    detail?: string
  } | null
}

export interface InferenceTaskDetailResponse extends InferenceTaskResponse {
  files: InferenceTaskFileResult[]
}

export type InferenceTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'partial_failed'

export interface HealthResponse {
  status: string
  version?: string
  model_loaded?: boolean
  engine?: string
  check?: string
  request_id?: string
}

export interface ReportBatchSummary {
  batch_id: string
  device_id: string
  report_time: number
  result_count: number
  total_detections: number
  created_at: number
}

export type ReviewStatus = 'pending' | 'confirmed' | 'false_positive' | 'ignored'

export interface ReportFrameReview {
  frame_id: number
  status: ReviewStatus
  note: string
  reviewer: string
  updated_at: number
}

export interface ReportFrameResult {
  frame_id: number
  timestamp: number
  source_id: string
  detections: DetectionBox[]
  inference_time_ms: number
  metadata: Record<string, unknown>
  review?: ReportFrameReview | null
}

export interface ReportRecordResponse {
  status: string
  batch_id: string
  device_id: string
  report_time: number
  result_count: number
  total_detections: number
  created_at: number
  results: ReportFrameResult[]
  payload: Record<string, unknown>
  request_id?: string
}

export interface ReportBatchListResponse {
  status: string
  count: number
  items: ReportBatchSummary[]
  request_id?: string
}

export interface ReportDeviceSummary {
  device_id: string
  batch_count: number
  result_count: number
  total_detections: number
  last_report_time: number
  last_batch_id: string
  last_created_at: number
  site_name: string
  display_name: string
  note: string
}

export interface ReportDeviceListResponse {
  status: string
  count: number
  items: ReportDeviceSummary[]
  request_id?: string
}

export interface ReportReviewRequest {
  status: ReviewStatus
  note: string
  reviewer: string
}

export interface ReportReviewResponse {
  status: string
  batch_id: string
  review: ReportFrameReview
  request_id?: string
}

export interface ReportDeviceMetadataRequest {
  site_name: string
  display_name: string
  note: string
}

export interface ReportDeviceMetadataResponse {
  device_id: string
  site_name: string
  display_name: string
  note: string
  updated_at: number
}

export interface AlertSummaryResponse {
  status: string
  stale_device_count: number
  failed_task_count: number
  partial_failed_task_count: number
  ready_failure_count: number
  request_id?: string
}

export interface DetectionReportFinding {
  label: string
  label_cn: string
  count: number
  max_confidence: number
  risk_level: string
  action: string
}

export interface DetectionReportResponse {
  title: string
  summary: string
  risk_level: string
  finding_count: number
  total_detections: number
  findings: DetectionReportFinding[]
  recommendations: string[]
  llm_context: Record<string, unknown>
  generated_by: 'template' | 'llm'
  request_id?: string
}

export interface AuditLogResponse {
  event_type: string
  resource_id: string
  actor: string
  request_id: string
  detail_json: string
  created_at: number
}

export interface ErrorResponse {
  code: string
  message: string
  detail?: string
  request_id?: string
}
