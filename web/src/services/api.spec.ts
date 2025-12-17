import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import type { HealthResponse, InferenceResponse } from '@/types/api'

// Mock axios
vi.mock('axios')

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mocked(axios.create).mockReturnValue({
  get: mockGet,
  post: mockPost
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any)

// 重新导入 apiService（在 mock 之后）
const { apiService } = await import('@/services/api')

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
          }
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
  })

  describe('Client Configuration', () => {
    it('apiService 实例应该存在', () => {
      expect(apiService).toBeDefined()
      expect(apiService.health).toBeDefined()
      expect(apiService.analyze).toBeDefined()
    })
  })
})
