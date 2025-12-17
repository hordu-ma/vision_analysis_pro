import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import HealthStatus from '@/components/HealthStatus.vue'
import { apiService } from '@/services/api'
import type { HealthResponse } from '@/types/api'

// Mock API service
vi.mock('@/services/api', () => ({
  apiService: {
    health: vi.fn()
  }
}))

describe('HealthStatus.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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

  it('健康检查失败时应该显示为不健康', async () => {
    vi.mocked(apiService.health).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(HealthStatus)
    await flushPromises()

    expect(wrapper.vm.healthData).toEqual({ status: 'unhealthy' })
  })

  it('加载中时应该显示检查中状态', async () => {
    let resolvePromise: () => void
    const promise = new Promise<HealthResponse>(resolve => {
      resolvePromise = () => resolve({ status: 'healthy' })
    })

    vi.mocked(apiService.health).mockReturnValue(promise)

    const wrapper = mount(HealthStatus)

    // 等待下一个 tick 让 loading 状态生效
    await wrapper.vm.$nextTick()

    // 此时应该显示检查中
    expect(wrapper.vm.loading).toBe(true)
    expect(wrapper.vm.statusText).toBe('检查中...')
  })

  it('应该正确计算状态类型', async () => {
    const mockHealthData: HealthResponse = {
      status: 'healthy'
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    expect(wrapper.vm.statusType).toBe('success')
  })

  it('不健康状态应该返回danger类型', async () => {
    const mockHealthData: HealthResponse = {
      status: 'unhealthy'
    }

    vi.mocked(apiService.health).mockResolvedValue(mockHealthData)

    const wrapper = mount(HealthStatus)
    await flushPromises()

    expect(wrapper.vm.statusType).toBe('danger')
  })
})
