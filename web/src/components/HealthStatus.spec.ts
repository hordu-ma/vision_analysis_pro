import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HealthStatus from '@/components/HealthStatus.vue'
import type { HealthResponse } from '@/types/api'

// Mock API service
vi.mock('@/services/api', () => ({
  apiService: {
    health: vi.fn()
  },
  ApiError: class ApiError extends Error {
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
}))

// 导入 mock 后的模块
import { apiService } from '@/services/api'

describe('HealthStatus.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('应该在挂载时调用健康检查', async () => {
    const mockHealthData: HealthResponse = {
      status: 'healthy',
      version: '0.1.0',
      model_loaded: true,
      engine: 'YOLOInferenceEngine'
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    mount(HealthStatus)
    await flushPromises()

    expect(apiService.health).toHaveBeenCalledTimes(1)
  })

  it('应该正确显示健康状态', async () => {
    const mockHealthData: HealthResponse = {
      status: 'healthy',
      version: '0.1.0',
      model_loaded: true
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    expect(wrapper.text()).toContain('服务正常')
  })

  it('应该正确显示不健康状态', async () => {
    const mockHealthData: HealthResponse = {
      status: 'unhealthy'
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    expect(wrapper.text()).toContain('服务异常')
  })

  it('健康检查失败时应该显示连接失败', async () => {
    vi.mocked(apiService.health).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(HealthStatus)
    await flushPromises()

    // 新行为：错误时 healthData 为 null，显示"连接失败"
    const component = wrapper.vm as unknown as { healthData: HealthResponse | null }
    expect(component.healthData).toBeNull()
    expect(wrapper.text()).toContain('连接失败')
  })

  it('加载中时应该显示检查中状态', async () => {
    const promise = new Promise<HealthResponse>(resolve => {
      setTimeout(() => resolve({ status: 'healthy', model_loaded: true }), 100)
    })

    vi.mocked(apiService.health).mockReturnValue(promise)

    const wrapper = mount(HealthStatus)

    // 等待下一个 tick 让 loading 状态生效
    await wrapper.vm.$nextTick()

    // 此时应该显示检查中
    const component = wrapper.vm as unknown as { loading: boolean; statusText: string }
    expect(component.loading).toBe(true)
    expect(component.statusText).toBe('检查中...')
  })

  it('健康且模型已加载时状态类型应该是 success', async () => {
    const mockHealthData: HealthResponse = {
      status: 'healthy',
      model_loaded: true
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    const component = wrapper.vm as unknown as { statusType: string }
    expect(component.statusType).toBe('success')
  })

  it('健康但模型未加载时状态类型应该是 warning', async () => {
    const mockHealthData: HealthResponse = {
      status: 'healthy',
      model_loaded: false
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    const component = wrapper.vm as unknown as { statusType: string }
    expect(component.statusType).toBe('warning')
    expect(wrapper.text()).toContain('模型未加载')
  })

  it('不健康状态应该返回 danger 类型', async () => {
    const mockHealthData: HealthResponse = {
      status: 'unhealthy'
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    const component = wrapper.vm as unknown as { statusType: string }
    expect(component.statusType).toBe('danger')
  })

  it('连接失败时状态类型应该是 danger', async () => {
    vi.mocked(apiService.health).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(HealthStatus)
    await flushPromises()

    const component = wrapper.vm as unknown as { statusType: string }
    expect(component.statusType).toBe('danger')
  })
})
