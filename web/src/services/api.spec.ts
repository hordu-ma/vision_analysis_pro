import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import type { HealthResponse, InferenceResponse } from '@/types/api'

// Mock axios
vi.mock('axios')

const mockGet = vi.fn()
const mockPost = vi.fn()
const mockInterceptors = {
  request: { use: vi.fn() },
  response: { use: vi.fn() }
}

vi.mocked(axios.create).mockReturnValue({
  get: mockGet,
  post: mockPost,
  interceptors: mockInterceptors
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any)

// Mock ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn()
  }
}))

// 重新导入 apiService（在 mock 之后）
const { apiService, ApiError } = await import('@/services/api')

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('health()', () => {
    it('应该调用健康检查接口并返回数据', async () => {
      const mockResponse: HealthResponse = {
        status: 'healthy',
        version: '0.1.0',
        model_loaded: true,
        engine: 'YOLOInferenceEngine'
      }

      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.health()

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/health')
    })

    it('健康检查失败时应该抛出错误', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      await expect(apiService.health()).rejects.toThrow('Network error')
    })
  })

  describe('analyze()', () => {
    it('应该正确上传文件并返回推理结果', async () => {
      const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      const mockResponse: InferenceResponse = {
        filename: 'test.jpg',
        detections: [
          {
            label: 'crack',
            confidence: 0.95,
            bbox: [100, 150, 300, 400]
          }
        ],
        metadata: {
          engine: 'YOLOInferenceEngine'
        }
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      const result = await apiService.analyze(mockFile, true)

      expect(result).toEqual(mockResponse)
      expect(mockPost).toHaveBeenCalledWith(
        '/inference/image?visualize=true',
        expect.any(FormData),
        expect.objectContaining({
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 120000,
          onUploadProgress: expect.any(Function)
        })
      )
    })

    it('应该支持不带可视化的请求', async () => {
      const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      const mockResponse: InferenceResponse = {
        filename: 'test.jpg',
        detections: [],
        metadata: { engine: 'Test' }
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      await apiService.analyze(mockFile, false)

      expect(mockPost).toHaveBeenCalledWith(
        '/inference/image?visualize=false',
        expect.any(FormData),
        expect.any(Object)
      )
    })

    it('上传失败时应该抛出错误', async () => {
      const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' })

      mockPost.mockRejectedValue(new Error('Upload failed'))

      await expect(apiService.analyze(mockFile)).rejects.toThrow('Upload failed')
    })

    it('应该支持上传进度回调', async () => {
      const mockFile = new File(['test'], 'test.jpg', { type: 'image/jpeg' })
      const mockResponse: InferenceResponse = {
        filename: 'test.jpg',
        detections: [],
        metadata: { engine: 'Test' }
      }
      const progressCallback = vi.fn()

      mockPost.mockImplementation((_url, _data, config) => {
        // 模拟进度回调
        if (config?.onUploadProgress) {
          config.onUploadProgress({ loaded: 50, total: 100 })
          config.onUploadProgress({ loaded: 100, total: 100 })
        }
        return Promise.resolve({ data: mockResponse })
      })

      await apiService.analyze(mockFile, true, progressCallback)

      expect(progressCallback).toHaveBeenCalledWith(50)
      expect(progressCallback).toHaveBeenCalledWith(100)
    })
  })

  describe('isServiceAvailable()', () => {
    it('服务健康且模型已加载时应返回 true', async () => {
      mockGet.mockResolvedValue({
        data: { status: 'healthy', model_loaded: true }
      })

      const result = await apiService.isServiceAvailable()

      expect(result).toBe(true)
    })

    it('服务健康但模型未加载时应返回 false', async () => {
      mockGet.mockResolvedValue({
        data: { status: 'healthy', model_loaded: false }
      })

      const result = await apiService.isServiceAvailable()

      expect(result).toBe(false)
    })

    it('服务不健康时应返回 false', async () => {
      mockGet.mockResolvedValue({
        data: { status: 'unhealthy', model_loaded: true }
      })

      const result = await apiService.isServiceAvailable()

      expect(result).toBe(false)
    })

    it('请求失败时应返回 false', async () => {
      mockGet.mockRejectedValue(new Error('Network error'))

      const result = await apiService.isServiceAvailable()

      expect(result).toBe(false)
    })
  })

  describe('Client Configuration', () => {
    it('apiService 实例应该存在', () => {
      expect(apiService).toBeDefined()
      expect(apiService.health).toBeDefined()
      expect(apiService.analyze).toBeDefined()
      expect(apiService.isServiceAvailable).toBeDefined()
      expect(apiService.showError).toBeDefined()
    })
  })

  describe('ApiError', () => {
    it('应该正确创建 ApiError 实例', () => {
      const error = new ApiError('TEST_ERROR', 'Test message', 500, 'Detail info')

      expect(error.name).toBe('ApiError')
      expect(error.code).toBe('TEST_ERROR')
      expect(error.message).toBe('Test message')
      expect(error.status).toBe(500)
      expect(error.detail).toBe('Detail info')
    })

    it('应该是 Error 的实例', () => {
      const error = new ApiError('TEST', 'Test', 400)

      expect(error).toBeInstanceOf(Error)
      expect(error).toBeInstanceOf(ApiError)
    })
  })
})
