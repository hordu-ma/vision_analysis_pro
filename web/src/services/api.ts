import axios, { type AxiosInstance, type AxiosError, type AxiosProgressEvent } from 'axios'
import { ElMessage } from 'element-plus'
import type { HealthResponse, InferenceResponse, ErrorResponse } from '@/types/api'

/**
 * API 错误类
 */
export class ApiError extends Error {
  code: string
  detail?: string
  status: number

  constructor(code: string, message: string, status: number, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
    this.status = status
  }
}

/**
 * 错误码映射
 */
const ERROR_MESSAGES: Record<string, string> = {
  NETWORK_ERROR: '网络连接失败，请检查网络',
  TIMEOUT: '请求超时，请重试',
  SERVER_ERROR: '服务器错误，请稍后重试',
  MODEL_NOT_LOADED: '模型未加载，请联系管理员',
  INVALID_FILE: '文件格式无效',
  FILE_TOO_LARGE: '文件过大',
  UNAUTHORIZED: '未授权访问',
  NOT_FOUND: '资源不存在',
  SERVICE_UNAVAILABLE: '服务暂不可用'
}

/**
 * 获取友好的错误消息
 */
function getErrorMessage(code: string, defaultMessage?: string): string {
  return ERROR_MESSAGES[code] || defaultMessage || '未知错误'
}

/**
 * 上传进度回调类型
 */
export type UploadProgressCallback = (progress: number) => void

/**
 * API 服务类
 */
class ApiService {
  private client: AxiosInstance
  private isShowingError = false

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 60000, // 60秒超时（考虑大文件上传和推理时间）
      headers: {
        'Content-Type': 'application/json'
      }
    })

    this.setupInterceptors()
  }

  /**
   * 设置请求/响应拦截器
   */
  private setupInterceptors(): void {
    // 请求拦截器
    this.client.interceptors.request.use(
      config => {
        // 可以在这里添加 token 等认证信息
        // const token = localStorage.getItem('token')
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`
        // }
        return config
      },
      error => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.client.interceptors.response.use(
      response => {
        return response
      },
      (error: AxiosError<ErrorResponse>) => {
        const apiError = this.handleError(error)
        return Promise.reject(apiError)
      }
    )
  }

  /**
   * 统一错误处理
   */
  private handleError(error: AxiosError<ErrorResponse>): ApiError {
    let code = 'UNKNOWN_ERROR'
    let message = '未知错误'
    let status = 0
    let detail: string | undefined

    if (error.response) {
      // 服务器返回错误响应
      status = error.response.status
      const data = error.response.data

      if (data && typeof data === 'object') {
        code = data.code || `HTTP_${status}`
        message = data.message || getErrorMessage(code)
        detail = data.detail
      } else {
        // 处理 HTTP 状态码
        switch (status) {
          case 400:
            code = 'BAD_REQUEST'
            message = '请求参数错误'
            break
          case 401:
            code = 'UNAUTHORIZED'
            message = getErrorMessage('UNAUTHORIZED')
            break
          case 403:
            code = 'FORBIDDEN'
            message = '禁止访问'
            break
          case 404:
            code = 'NOT_FOUND'
            message = getErrorMessage('NOT_FOUND')
            break
          case 413:
            code = 'FILE_TOO_LARGE'
            message = getErrorMessage('FILE_TOO_LARGE')
            break
          case 422:
            code = 'VALIDATION_ERROR'
            message = '数据验证失败'
            break
          case 500:
            code = 'SERVER_ERROR'
            message = getErrorMessage('SERVER_ERROR')
            break
          case 502:
          case 503:
          case 504:
            code = 'SERVICE_UNAVAILABLE'
            message = getErrorMessage('SERVICE_UNAVAILABLE')
            break
          default:
            code = `HTTP_${status}`
            message = `请求失败 (${status})`
        }
      }
    } else if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      // 超时错误
      code = 'TIMEOUT'
      message = getErrorMessage('TIMEOUT')
    } else if (error.code === 'ERR_NETWORK' || !navigator.onLine) {
      // 网络错误
      code = 'NETWORK_ERROR'
      message = getErrorMessage('NETWORK_ERROR')
    } else {
      // 其他错误
      code = error.code || 'UNKNOWN_ERROR'
      message = error.message || '请求失败'
    }

    return new ApiError(code, message, status, detail)
  }

  /**
   * 显示错误消息（防抖）
   */
  showError(error: ApiError | Error): void {
    if (this.isShowingError) return

    this.isShowingError = true
    const message = error instanceof ApiError ? error.message : error.message || '操作失败'

    ElMessage.error({
      message,
      duration: 3000,
      onClose: () => {
        this.isShowingError = false
      }
    })
  }

  /**
   * 健康检查
   */
  async health(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health')
    return response.data
  }

  /**
   * 图像分析
   * @param file 图像文件
   * @param visualize 是否生成可视化结果
   * @param onProgress 上传进度回调
   */
  async analyze(
    file: File,
    visualize = true,
    onProgress?: UploadProgressCallback
  ): Promise<InferenceResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<InferenceResponse>(
      `/inference/image?visualize=${visualize}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 120000, // 推理可能需要更长时间
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(progress)
          }
        }
      }
    )
    return response.data
  }

  /**
   * 检查服务可用性
   */
  async isServiceAvailable(): Promise<boolean> {
    try {
      const health = await this.health()
      return health.status === 'healthy' && health.model_loaded === true
    } catch {
      return false
    }
  }
}

// 单例导出
export const apiService = new ApiService()
