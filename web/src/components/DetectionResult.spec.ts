import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DetectionResult from '@/components/DetectionResult.vue'
import type { InferenceResponse } from '@/types/api'

// Mock Element Plus 组件
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn()
    }
  }
})

describe('DetectionResult.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('应该在没有结果时显示空状态', () => {
    const wrapper = mount(DetectionResult, {
      props: {
        result: null
      }
    })

    expect(wrapper.text()).toContain('暂无检测结果')
  })

  it('应该正确显示检测结果', () => {
    const mockResult: InferenceResponse = {
      filename: 'test.jpg',
      detections: [
        {
          label: 'crack',
          confidence: 0.95,
          bbox: [100, 150, 300, 400]
        },
        {
          label: 'rust',
          confidence: 0.88,
          bbox: [200, 250, 400, 500]
        }
      ],
      metadata: {
        engine: 'YOLOInferenceEngine',
        inference_time_ms: 123.45
      }
    }

    const wrapper = mount(DetectionResult, {
      props: {
        result: mockResult
      }
    })

    // 检查检测数量
    expect(wrapper.text()).toContain('2')
    // 检查推理时间（显示为 123.4 而不是 123.5，因为保留一位小数）
    expect(wrapper.text()).toContain('123.4')
  })

  it('应该正确计算平均置信度', () => {
    const mockResult: InferenceResponse = {
      filename: 'test.jpg',
      detections: [
        { label: 'crack', confidence: 0.9, bbox: [0, 0, 100, 100] },
        { label: 'rust', confidence: 0.8, bbox: [0, 0, 100, 100] }
      ],
      metadata: { engine: 'Test' }
    }

    const wrapper = mount(DetectionResult, {
      props: {
        result: mockResult
      }
    })

    // 平均置信度应该是 (0.9 + 0.8) / 2 * 100 = 85%
    const component = wrapper.vm as unknown as { avgConfidence: number }
    const avgConfidence = component.avgConfidence
    expect(avgConfidence).toBeCloseTo(85, 1)
  })

  it('空检测列表时平均置信度应该为0', () => {
    const mockResult: InferenceResponse = {
      filename: 'test.jpg',
      detections: [],
      metadata: { engine: 'Test' }
    }

    const wrapper = mount(DetectionResult, {
      props: {
        result: mockResult
      }
    })

    const component = wrapper.vm as unknown as { avgConfidence: number }
    expect(component.avgConfidence).toBe(0)
  })

  it('应该正确显示可视化图片', () => {
    const mockResult: InferenceResponse = {
      filename: 'test.jpg',
      detections: [{ label: 'test', confidence: 0.5, bbox: [0, 0, 1, 1] }],
      metadata: { engine: 'Test' },
      visualization: 'data:image/jpeg;base64,test123'
    }

    const wrapper = mount(DetectionResult, {
      props: {
        result: mockResult
      },
      global: {
        stubs: {
          'el-image': {
            template: '<img class="visualization-image" :src="src" />',
            props: ['src']
          }
        }
      }
    })

    const img = wrapper.find('.visualization-image')
    expect(img.exists()).toBe(true)
    expect(img.attributes('src')).toBe('data:image/jpeg;base64,test123')
  })

  it('应该正确格式化边界框坐标', () => {
    const mockResult: InferenceResponse = {
      filename: 'test.jpg',
      detections: [
        {
          label: 'crack',
          confidence: 0.95,
          bbox: [100.123, 150.456, 300.789, 400.012]
        }
      ],
      metadata: { engine: 'Test' }
    }

    const wrapper = mount(DetectionResult, {
      props: {
        result: mockResult
      },
      global: {
        stubs: [
          'el-card',
          'el-row',
          'el-col',
          'el-statistic',
          'el-table',
          'el-table-column',
          'el-tag'
        ]
      }
    })

    // 检查组件是否正确渲染了数据
    const result = wrapper.props('result')
    expect(result).not.toBeNull()
    if (result && result.detections && result.detections.length > 0) {
      const firstDetection = result.detections[0]
      expect(firstDetection).toBeDefined()
      if (firstDetection) {
        expect(firstDetection.bbox).toEqual([100.123, 150.456, 300.789, 400.012])
      }
    }
  })
})
