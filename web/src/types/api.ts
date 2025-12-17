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
  }
  visualization?: string
}

export interface HealthResponse {
  status: string
  version?: string
  model_loaded?: boolean
  engine?: string
}

export interface ErrorResponse {
  code: string
  message: string
  detail?: string
}
