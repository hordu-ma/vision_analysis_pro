import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ReportBatchList from '@/components/ReportBatchList.vue'
import type { ReportBatchSummary } from '@/types/api'

// Custom stubs for child components that must emit events
const WorkspaceActionButtonStub = {
  name: 'WorkspaceActionButton',
  template:
    '<button class="workspace-action-btn" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>',
  props: ['label', 'icon', 'tone', 'compact', 'disabled'],
  emits: ['click']
}

const WorkspaceRecordItemStub = {
  name: 'WorkspaceRecordItem',
  template: '<div class="workspace-record-item" @click="$emit(\'select\')">{{ title }}</div>',
  props: ['title', 'description', 'meta', 'badge', 'badgeTone'],
  emits: ['select']
}

const WorkspaceSectionHeaderStub = {
  name: 'WorkspaceSectionHeader',
  template: '<div class="workspace-section-header"><slot /><slot name="actions" /></div>',
  props: ['title', 'caption']
}

const globalStubs = {
  WorkspaceActionButton: WorkspaceActionButtonStub,
  WorkspaceRecordItem: WorkspaceRecordItemStub,
  WorkspaceSectionHeader: WorkspaceSectionHeaderStub
}

const makeBatch = (overrides: Partial<ReportBatchSummary> = {}): ReportBatchSummary => ({
  batch_id: 'batch-001',
  device_id: 'edge-device-01',
  report_time: 1700000000,
  result_count: 10,
  total_detections: 3,
  created_at: 1700000001,
  ...overrides
})

describe('ReportBatchList.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('batches 为空时显示空状态', () => {
    const wrapper = mount(ReportBatchList, {
      props: { batches: [] },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('暂无批次记录')
  })

  it('batches 不为空时渲染记录列表', () => {
    const wrapper = mount(ReportBatchList, {
      props: {
        batches: [makeBatch({ batch_id: 'batch-001' }), makeBatch({ batch_id: 'batch-002' })]
      },
      global: { stubs: globalStubs }
    })
    const items = wrapper.findAll('.workspace-record-item')
    expect(items).toHaveLength(2)
  })

  it('没有 activeDeviceId 时不显示筛选 chip', () => {
    const wrapper = mount(ReportBatchList, {
      props: { batches: [makeBatch()] },
      global: { stubs: globalStubs }
    })
    expect(wrapper.find('.filter-chip').exists()).toBe(false)
  })

  it('传入 activeDeviceId 时显示筛选 chip', () => {
    const wrapper = mount(ReportBatchList, {
      props: { batches: [makeBatch()], activeDeviceId: 'edge-device-01' },
      global: { stubs: globalStubs }
    })
    expect(wrapper.find('.filter-chip').exists()).toBe(true)
    expect(wrapper.find('.filter-chip').text()).toContain('edge-device-01')
  })

  it('点击刷新按钮触发 refresh 事件', async () => {
    const wrapper = mount(ReportBatchList, {
      props: { batches: [] },
      global: { stubs: globalStubs }
    })
    const buttons = wrapper.findAll('.workspace-action-btn')
    const refreshBtn = buttons.find(b => b.text() === '刷新')
    expect(refreshBtn).toBeDefined()
    await refreshBtn!.trigger('click')
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })

  it('activeDeviceId 存在时点击清除筛选触发 clear-filter 事件', async () => {
    const wrapper = mount(ReportBatchList, {
      props: { batches: [makeBatch()], activeDeviceId: 'edge-device-01' },
      global: { stubs: globalStubs }
    })
    const buttons = wrapper.findAll('.workspace-action-btn')
    const clearBtn = buttons.find(b => b.text() === '清除筛选')
    expect(clearBtn).toBeDefined()
    await clearBtn!.trigger('click')
    expect(wrapper.emitted('clear-filter')).toBeTruthy()
  })

  it('点击批次记录触发 view-detail 事件并传递 batch_id', async () => {
    const wrapper = mount(ReportBatchList, {
      props: { batches: [makeBatch({ batch_id: 'batch-xyz' })] },
      global: { stubs: globalStubs }
    })
    const item = wrapper.find('.workspace-record-item')
    await item.trigger('click')
    const emitted = wrapper.emitted('view-detail')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual(['batch-xyz'])
  })

  it('点击下一页触发 page 事件并传递 offset', async () => {
    const wrapper = mount(ReportBatchList, {
      props: {
        batches: [makeBatch({ batch_id: 'batch-001' }), makeBatch({ batch_id: 'batch-002' })],
        total: 5,
        limit: 2,
        offset: 0
      },
      global: { stubs: globalStubs }
    })
    expect(wrapper.get('[data-testid="report-pagination"]').text()).toContain('1-2 / 5')
    const nextBtn = wrapper.findAll('.workspace-action-btn').find(b => b.text() === '下一页')
    expect(nextBtn).toBeDefined()
    await nextBtn!.trigger('click')
    expect(wrapper.emitted('page')![0]).toEqual([2])
  })
})
