import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import AuditLogList from '@/components/AuditLogList.vue'
import type { AuditLogResponse } from '@/types/api'

const globalStubs = {
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-input': {
    template:
      '<input class="el-input" :value="modelValue" @input="$emit(\'input\', $event.target.value)" />',
    props: ['modelValue', 'placeholder', 'size', 'class'],
    emits: ['input']
  },
  'el-button': {
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
    props: ['text', 'size', 'disabled'],
    emits: ['click']
  },
  'el-table': { template: '<div><slot /></div>', props: ['data', 'stripe'] },
  'el-table-column': {
    template: '<div class="el-table-column" />',
    props: ['prop', 'label', 'minWidth', 'width']
  }
}

const makeLog = (overrides: Partial<AuditLogResponse> = {}): AuditLogResponse => ({
  event_type: 'device_metadata_updated',
  resource_id: 'device-a',
  actor: 'tester',
  request_id: 'req-1',
  detail_json: '{"site_name":"西区"}',
  created_at: 1700000001,
  ...overrides
})

describe('AuditLogList.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('logs 为空时显示空状态', () => {
    const wrapper = mount(AuditLogList, {
      props: { logs: [], actorFilter: '' },
      global: { stubs: globalStubs }
    })
    expect(wrapper.text()).toContain('暂无审计记录')
  })

  it('点击刷新触发 refresh 事件', async () => {
    const wrapper = mount(AuditLogList, {
      props: { logs: [makeLog()], actorFilter: '' },
      global: { stubs: globalStubs }
    })
    const refreshBtn = wrapper.findAll('button').find(button => button.text() === '刷新')
    expect(refreshBtn).toBeDefined()
    await refreshBtn!.trigger('click')
    expect(wrapper.emitted('refresh')).toBeTruthy()
  })

  it('点击下一页触发 page 事件', async () => {
    const wrapper = mount(AuditLogList, {
      props: {
        logs: [makeLog({ resource_id: 'device-a' }), makeLog({ resource_id: 'device-b' })],
        actorFilter: '',
        total: 5,
        limit: 2,
        offset: 0
      },
      global: { stubs: globalStubs }
    })

    expect(wrapper.get('[data-testid="audit-pagination"]').text()).toContain('1-2 / 5')
    const nextBtn = wrapper.findAll('button').find(button => button.text() === '下一页')
    expect(nextBtn).toBeDefined()
    await nextBtn!.trigger('click')
    expect(wrapper.emitted('page')![0]).toEqual([2])
  })

  it('输入操作者筛选时触发 update:actorFilter', async () => {
    const wrapper = mount(AuditLogList, {
      props: { logs: [makeLog()], actorFilter: '' },
      global: { stubs: globalStubs }
    })

    await wrapper.get('.el-input').setValue('reviewer-a')
    expect(wrapper.emitted('update:actorFilter')![0]).toEqual(['reviewer-a'])
  })
})
