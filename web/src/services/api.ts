import axios, { type AxiosInstance } from 'axios'
import type { HealthResponse, InferenceResponse } from '@/types/api'

class ApiService {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health')
    return response.data
  }

  async analyze(file: File, visualize = true): Promise<InferenceResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<InferenceResponse>(
      `/inference/image?visualize=${visualize}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    return response.data
  }
}

export const apiService = new ApiService()
