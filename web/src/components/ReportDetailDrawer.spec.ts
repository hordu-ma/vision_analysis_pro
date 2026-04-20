import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ReportDetailDrawer from '@/components/ReportDetailDrawer.vue'
import type { ReportRecordResponse } from '@/types/api'

// Stub el-drawer so that slot content is always rendered
const ElDrawerStub = {
  name: 'ElDrawer',
  template: '<div class="el-drawer-stub" :data-visible="modelValue"><slot /></div>',
  props: ['modelValue', 'size', 'title'],
  emits: ['close']
}

const globalStubs = {
  'el-drawer': ElDrawerStub,
  'el-descriptions': {
    template: '<div class="el-descriptions"><slot /></div>',
    props: ['column', 'border']
  },
  'el-descriptions-item': { template: '<div><slot /></div>', props: ['label'] },
  'el-button': {
    template: '<button @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'plain'],
    emits: ['click']
  },
  'el-collapse': { template: '<div><slot /></div>', props: ['accordion'] },
  'el-collapse-item': {
    template: '<div class="el-collapse-item"><slot /></div>',
    props: ['title', 'name']
  },
  'el-table': { template: '<table><slot /></table>', props: ['data', 'stripe', 'size'] },
  'el-table-column': {
    template: '<td><slot /></td>',
    props: ['prop', 'label', 'minWidth', 'width']
  },
  'el-form': { template: '<form><slot /></form>', props: ['labelWidth'] },
  'el-form-item': { template: '<div><slot /></div>', props: ['label'] },
  'el-select': { template: '<select />', props: ['modelValue', 'placeholder'] },
  'el-option': { template: '<option />', props: ['label', 'value'] },
  'el-input': { template: '<input />', props: ['modelValue', 'placeholder', 'type', 'rows'] }
}

const makeReport = (overrides: Partial<ReportRecordResponse> = {}): ReportRecordResponse => ({
  status: 'found',
  batch_id: 'batch-test-001',
  device_id: 'edge-device-01',
  report_time: 1700000000,
  result_count: 2,
  total_detections: 3,
  created_at: 1700000001,
  results: [],
  payload: {},
  ...overrides
})

describe('ReportDetailDrawer.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('visible=true 且 report 存在时渲染批次 ID', () => {
    const wrapper = mount(ReportDetailDrawer, {
      props: { visible: true, report: makeReport({ batch_id: 'batch-test-001' }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('batch-test-001')
  })

  it('visible=true 且 report 存在时渲染设备 ID', () => {
    const wrapper = mount(ReportDetailDrawer, {
      props: { visible: true, report: makeReport({ device_id: 'edge-device-99' }) },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('edge-device-99')
  })

  it('report 为 null 时不渲染批次内容', () => {
    const wrapper = mount(ReportDetailDrawer, {
      props: { visible: true, report: null },
      global: { stubs: globalStubs }
    })
    expect(wrapper.find('.detail-wrapper').exists()).toBe(false)
  })

  it('点击导出 CSV 按钮触发 export 事件并传递 batch_id', async () => {
    const wrapper = mount(ReportDetailDrawer, {
      props: { visible: true, report: makeReport({ batch_id: 'batch-export-001' }) },
      global: { stubs: globalStubs }
    })
    const buttons = wrapper.findAll('button')
    const exportBtn = buttons.find(b => b.text().includes('导出 CSV'))
    expect(exportBtn).toBeDefined()
    await exportBtn!.trigger('click')
    const emitted = wrapper.emitted('export')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual(['batch-export-001'])
  })

  it('el-drawer 的 close 事件触发 close 事件', async () => {
    const wrapper = mount(ReportDetailDrawer, {
      props: { visible: true, report: makeReport() },
      global: { stubs: globalStubs }
    })
    await wrapper.findComponent(ElDrawerStub).vm.$emit('close')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('visible prop 传递到 el-drawer', () => {
    const wrapper = mount(ReportDetailDrawer, {
      props: { visible: false, report: makeReport() },
      global: { stubs: globalStubs }
    })
    const drawer = wrapper.find('.el-drawer-stub')
    expect(drawer.attributes('data-visible')).toBe('false')
  })
})
