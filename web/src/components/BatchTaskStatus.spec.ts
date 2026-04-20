import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BatchTaskStatus from '@/components/BatchTaskStatus.vue'
import type { InferenceTaskResponse } from '@/types/api'

const globalStubs = {
  'el-card': { template: '<div><slot /><slot name="header" /></div>' },
  'el-tag': { template: '<span class="el-tag"><slot /></span>', props: ['type'] },
  'el-descriptions': { template: '<div><slot /></div>', props: ['column', 'border'] },
  'el-descriptions-item': { template: '<div><slot /></div>', props: ['label'] },
  'el-progress': {
    template: '<div class="el-progress" />',
    props: ['percentage', 'status']
  },
  'el-alert': {
    template: '<div class="el-alert" :title="title" :description="description"><slot /></div>',
    props: ['title', 'description', 'type', 'showIcon']
  },
  'el-button': {
    template: '<button @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'plain'],
    emits: ['click']
  }
}

const makeTask = (overrides: Partial<InferenceTaskResponse> = {}): InferenceTaskResponse => ({
  task_id: 'task-001',
  status: 'pending',
  created_at: 1700000000,
  updated_at: 1700000001,
  file_count: 5,
  completed_files: 0,
  progress: 0,
  results: [],
  metadata: {},
  ...overrides
})

describe('BatchTaskStatus.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('task 为 null 时不渲染卡片', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: null },
      global: { stubs: globalStubs }
    })
    expect(wrapper.find('.batch-task-card').exists()).toBe(false)
  })

  it('显示任务 ID', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ task_id: 'task-abc-123' }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('task-abc-123')
  })

  it('completed 状态时显示"已完成"标签', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'completed', progress: 100 }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('已完成')
  })

  it('failed 状态时显示"失败"标签', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'failed' }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('失败')
  })

  it('running 状态时显示"执行中"标签', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'running' }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('执行中')
  })

  it('failed 状态时显示重试按钮', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'failed' }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('重试当前任务')
  })

  it('partial_failed 状态时显示重试失败文件按钮', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'partial_failed', progress: 80 }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('重试失败文件')
  })

  it('completed 状态时显示复跑按钮和导出按钮', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'completed', progress: 100 }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('复跑当前任务')
    expect(wrapper.text()).toContain('查看详情')
  })

  it('failed 时点击重试触发 retry 事件', async () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'failed', task_id: 'task-retry' }) },
      global: { stubs: globalStubs }
    })
    const buttons = wrapper.findAll('button')
    const retryBtn = buttons.find(b => b.text() === '重试当前任务')
    expect(retryBtn).toBeDefined()
    await retryBtn!.trigger('click')
    const emitted = wrapper.emitted('retry')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual(['task-retry'])
  })

  it('task 有 error 时显示告警', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: {
        task: makeTask({
          status: 'failed',
          error: { code: 'INFERENCE_ERROR', message: '推理失败', detail: '模型加载失败' }
        })
      },
      global: { stubs: globalStubs }
    })
    expect(wrapper.find('.el-alert').exists()).toBe(true)
  })

  it('进度为 60 时显示进度条', () => {
    const wrapper = mount(BatchTaskStatus, {
      props: { task: makeTask({ status: 'running', progress: 60 }) },
      global: { stubs: globalStubs }
    })
    const progress = wrapper.find('.el-progress')
    expect(progress.exists()).toBe(true)
  })
})
