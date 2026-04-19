import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import type {
  HealthResponse,
  InferenceResponse,
  BatchInferenceResponse,
  InferenceTaskResponse,
  ReportBatchListResponse,
  ReportDeviceListResponse,
  ReportRecordResponse,
  ReportReviewResponse
} from '@/types/api'

// Mock axios
vi.mock('axios')

const mockGet = vi.fn()
const mockPost = vi.fn()
const mockPut = vi.fn()
const mockInterceptors = {
  request: { use: vi.fn() },
  response: { use: vi.fn() }
}

vi.mocked(axios.create).mockReturnValue({
  get: mockGet,
  post: mockPost,
  put: mockPut,
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

    it('应该支持批量上传并返回结果', async () => {
      const files = [
        new File(['a'], 'first.jpg', { type: 'image/jpeg' }),
        new File(['b'], 'second.jpg', { type: 'image/jpeg' })
      ]
      const mockResponse: BatchInferenceResponse = {
        files: [
          { filename: 'first.jpg', detections: [], metadata: { engine: 'Test' } },
          { filename: 'second.jpg', detections: [], metadata: { engine: 'Test' } }
        ],
        metadata: { file_count: 2, total_detections: 0 }
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      const result = await apiService.analyzeBatch(files, true)

      expect(result).toEqual(mockResponse)
      expect(mockPost).toHaveBeenCalledWith(
        '/inference/images?visualize=true',
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

    it('应该创建批量任务', async () => {
      const files = [new File(['a'], 'first.jpg', { type: 'image/jpeg' })]
      const mockResponse: InferenceTaskResponse = {
        task_id: 'task-001',
        status: 'pending',
        created_at: 1700000000,
        updated_at: 1700000000,
        file_count: 1,
        completed_files: 0,
        progress: 0,
        results: [],
        metadata: {}
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      const result = await apiService.createBatchTask(files, true)

      expect(result).toEqual(mockResponse)
      expect(mockPost).toHaveBeenCalledWith(
        '/inference/images/tasks?visualize=true',
        expect.any(FormData),
        expect.any(Object)
      )
    })

    it('应该查询批量任务', async () => {
      const mockResponse: InferenceTaskResponse = {
        task_id: 'task-001',
        status: 'completed',
        created_at: 1700000000,
        updated_at: 1700000001,
        file_count: 1,
        completed_files: 1,
        progress: 100,
        results: [],
        metadata: {}
      }

      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.getBatchTask('task-001')

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/inference/images/tasks/task-001')
    })

    it('应该获取批量任务列表', async () => {
      const mockResponse: InferenceTaskResponse[] = [
        {
          task_id: 'task-002',
          status: 'completed',
          created_at: 1700000002,
          updated_at: 1700000003,
          file_count: 2,
          completed_files: 2,
          progress: 100,
          results: [],
          metadata: {}
        }
      ]

      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.listBatchTasks(10)

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/inference/images/tasks?limit=10')
    })

    it('应该按状态筛选批量任务列表', async () => {
      const mockResponse: InferenceTaskResponse[] = []
      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.listBatchTasks(10, 'failed')

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/inference/images/tasks?limit=10&status=failed')
    })

    it('应该重试失败任务', async () => {
      const mockResponse: InferenceTaskResponse = {
        task_id: 'task-retry',
        status: 'pending',
        created_at: 1700000000,
        updated_at: 1700000000,
        file_count: 1,
        completed_files: 0,
        progress: 0,
        results: [],
        metadata: { source_task_id: 'task-failed', replay_mode: 'retry' }
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      const result = await apiService.retryBatchTask('task-failed')

      expect(result).toEqual(mockResponse)
      expect(mockPost).toHaveBeenCalledWith('/inference/images/tasks/task-failed/retry')
    })

    it('应该复跑已完成任务', async () => {
      const mockResponse: InferenceTaskResponse = {
        task_id: 'task-rerun',
        status: 'pending',
        created_at: 1700000000,
        updated_at: 1700000000,
        file_count: 1,
        completed_files: 0,
        progress: 0,
        results: [],
        metadata: { source_task_id: 'task-completed', replay_mode: 'rerun' }
      }

      mockPost.mockResolvedValue({ data: mockResponse })

      const result = await apiService.rerunBatchTask('task-completed')

      expect(result).toEqual(mockResponse)
      expect(mockPost).toHaveBeenCalledWith('/inference/images/tasks/task-completed/rerun')
    })

    it('应该导出已完成任务 CSV', async () => {
      const blob = new Blob(['task_id,filename'], { type: 'text/csv' })
      mockGet.mockResolvedValue({ data: blob })

      const result = await apiService.exportBatchTaskCsv('task-completed')

      expect(result).toBe(blob)
      expect(mockGet).toHaveBeenCalledWith('/inference/images/tasks/task-completed/export.csv', {
        responseType: 'blob'
      })
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

  describe('report queries', () => {
    it('应该获取最近批次列表', async () => {
      const mockResponse: ReportBatchListResponse = {
        status: 'ok',
        count: 1,
        items: [
          {
            batch_id: 'batch-001',
            device_id: 'device-a',
            report_time: 1700000000,
            result_count: 1,
            total_detections: 2,
            created_at: 1700000001
          }
        ]
      }

      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.listReportBatches(20, 'device-a')

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/reports/batches?limit=20&device_id=device-a')
    })

    it('应该获取设备概览列表', async () => {
      const mockResponse: ReportDeviceListResponse = {
        status: 'ok',
        count: 1,
        items: [
          {
            device_id: 'device-a',
            batch_count: 2,
            result_count: 4,
            total_detections: 5,
            last_report_time: 1700000000,
            last_batch_id: 'batch-002',
            last_created_at: 1700000001
          }
        ]
      }

      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.listReportDevices(10)

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/reports/devices?limit=10')
    })

    it('应该获取批次详情', async () => {
      const mockResponse: ReportRecordResponse = {
        status: 'found',
        batch_id: 'batch-001',
        device_id: 'device-a',
        report_time: 1700000000,
        result_count: 1,
        total_detections: 2,
        created_at: 1700000001,
        results: [],
        payload: {}
      }

      mockGet.mockResolvedValue({ data: mockResponse })

      const result = await apiService.getReport('batch-001')

      expect(result).toEqual(mockResponse)
      expect(mockGet).toHaveBeenCalledWith('/report/batch-001')
    })

    it('应该更新人工复核结果', async () => {
      const mockResponse: ReportReviewResponse = {
        status: 'updated',
        batch_id: 'batch-001',
        review: {
          frame_id: 1,
          status: 'confirmed',
          note: '人工确认',
          reviewer: 'alice',
          updated_at: 1700000002
        }
      }

      mockPut.mockResolvedValue({ data: mockResponse })

      const result = await apiService.updateReportReview('batch-001', 1, {
        status: 'confirmed',
        note: '人工确认',
        reviewer: 'alice'
      })

      expect(result).toEqual(mockResponse)
      expect(mockPut).toHaveBeenCalledWith('/report/batch-001/reviews/1', {
        status: 'confirmed',
        note: '人工确认',
        reviewer: 'alice'
      })
    })

    it('应该导出批次 CSV', async () => {
      const blob = new Blob(['a,b'], { type: 'text/csv' })
      mockGet.mockResolvedValue({ data: blob })

      const result = await apiService.exportReportCsv('batch-001')

      expect(result).toBe(blob)
      expect(mockGet).toHaveBeenCalledWith('/report/batch-001/export.csv', {
        responseType: 'blob'
      })
    })
  })

  describe('Client Configuration', () => {
    it('apiService 实例应该存在', () => {
      expect(apiService).toBeDefined()
      expect(apiService.health).toBeDefined()
      expect(apiService.analyze).toBeDefined()
      expect(apiService.analyzeBatch).toBeDefined()
      expect(apiService.createBatchTask).toBeDefined()
      expect(apiService.getBatchTask).toBeDefined()
      expect(apiService.listBatchTasks).toBeDefined()
      expect(apiService.retryBatchTask).toBeDefined()
      expect(apiService.rerunBatchTask).toBeDefined()
      expect(apiService.exportBatchTaskCsv).toBeDefined()
      expect(apiService.isServiceAvailable).toBeDefined()
      expect(apiService.listReportBatches).toBeDefined()
      expect(apiService.listReportDevices).toBeDefined()
      expect(apiService.getReport).toBeDefined()
      expect(apiService.updateReportReview).toBeDefined()
      expect(apiService.exportReportCsv).toBeDefined()
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
