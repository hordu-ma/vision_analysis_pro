import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ImageUpload from '@/components/ImageUpload.vue'

vi.mock('@/services/api', () => ({
  apiService: {
    analyzeImage: vi.fn(),
    analyzeBatchImages: vi.fn(),
    createBatchTask: vi.fn()
  },
  ApiError: class ApiError extends Error {
    code: string
    status: number
    constructor(code: string, message: string, status: number) {
      super(message)
      this.name = 'ApiError'
      this.code = code
      this.status = status
    }
  }
}))

vi.stubGlobal('URL', {
  createObjectURL: vi.fn(() => 'blob:mock-preview-url'),
  revokeObjectURL: vi.fn()
})

const globalStubs = {
  'el-upload': {
    template: '<div class="el-upload-stub"><slot /><slot name="tip" /></div>',
    props: ['autoUpload', 'limit', 'multiple', 'accept', 'disabled', 'fileList'],
    emits: ['change', 'exceed'],
    setup() {
      return { clearFiles: () => {} }
    }
  },
  'el-image': { template: '<img :src="src" />', props: ['src', 'fit'] },
  'el-button': {
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
    props: ['type', 'size', 'loading', 'disabled'],
    emits: ['click']
  },
  'el-radio-group': {
    template: '<div><slot /></div>',
    props: ['modelValue', 'disabled'],
    emits: ['update:modelValue']
  },
  'el-radio-button': {
    template: '<button @click="$emit(\'click\')">{{ label }}</button>',
    props: ['label']
  },
  'el-checkbox': {
    template: '<input type="checkbox" />',
    props: ['modelValue', 'label', 'disabled']
  },
  'el-progress': { template: '<div />', props: ['percentage', 'strokeWidth', 'indeterminate'] },
  'el-tag': { template: '<span><slot /></span>' },
  ProductIcon: { template: '<span />', props: ['name', 'spinning'] }
}

const exposedVm = (vm: unknown): Record<string, unknown> => vm as Record<string, unknown>

describe('ImageUpload.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('默认为单图模式', () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    const vm = exposedVm(wrapper.vm)
    expect(vm.uploadMode).toBe('single')
  })

  it('初始无文件时 selectedFile 为 null', () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    const vm = exposedVm(wrapper.vm)
    expect(vm.selectedFile).toBeNull()
  })

  it('初始无文件时 analyzing 为 false', () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    const vm = exposedVm(wrapper.vm)
    expect(vm.analyzing).toBe(false)
  })

  it('批量模式 selectedFiles 应该是数组', async () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    const vm = exposedVm(wrapper.vm)
    // Vue 3 script setup: refs are unwrapped in the vm proxy, assign directly
    vm.uploadMode = 'batch'
    await wrapper.vm.$nextTick()
    expect(Array.isArray(vm.selectedFiles)).toBe(true)
  })

  it('clearFile 应该清除 previewUrl 和 selectedFile', async () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    const vm = exposedVm(wrapper.vm)
    // Simulate a file being selected by setting refs directly
    vm.previewUrl = 'blob:mock-preview-url'
    vm.selectedFile = new File([''], 'test.jpg', {
      type: 'image/jpeg'
    })
    await wrapper.vm.$nextTick()
    // Call clearFile — el-upload stub exposes clearFiles as a no-op
    ;(vm.clearFile as () => void)()
    await wrapper.vm.$nextTick()
    expect(vm.previewUrl).toBe('')
    expect(vm.selectedFile).toBeNull()
  })

  it('previewUrl 为空时不显示预览区域', () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="image-preview"]').exists()).toBe(false)
  })

  it('存在分析按钮', () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="analyze-button"]').exists()).toBe(true)
  })

  it('数据卡片包含上传区域', () => {
    const wrapper = mount(ImageUpload, { global: { stubs: globalStubs } })
    expect(wrapper.find('[data-testid="upload-area"]').exists()).toBe(true)
  })
})
