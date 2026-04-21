<template>
  <button
    class="workspace-action"
    :class="[`tone-${tone}`, { compact }]"
    type="button"
    :disabled="disabled"
  >
    <ProductIcon :name="icon" class="action-icon" />
    <span>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import ProductIcon from '@/components/ProductIcon.vue'

withDefaults(
  defineProps<{
    label: string
    icon: 'spark-refresh' | 'archive-stack'
    tone?: 'default' | 'subtle'
    compact?: boolean
    disabled?: boolean
  }>(),
  {
    tone: 'default',
    compact: false,
    disabled: false
  }
)
</script>

<style scoped>
.workspace-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(241, 245, 249, 0.96));
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    color 0.18s ease,
    background 0.18s ease,
    transform 0.18s ease;
}

.workspace-action:hover {
  color: var(--brand);
  border-color: rgba(29, 78, 216, 0.24);
  background: rgba(239, 246, 255, 0.96);
  transform: translateY(-1px);
}

.workspace-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  transform: none;
}

.workspace-action.tone-subtle {
  background: rgba(255, 255, 255, 0.78);
}

.workspace-action.compact {
  min-height: 28px;
  padding: 0 9px;
  font-size: 11px;
}

.action-icon {
  font-size: 12px;
}
</style>
