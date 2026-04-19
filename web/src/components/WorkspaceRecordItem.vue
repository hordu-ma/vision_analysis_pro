<template>
  <article class="record-item" @click="emit('select')">
    <div class="record-main">
      <div class="record-heading">
        <div>
          <h4>{{ title }}</h4>
          <p>{{ description }}</p>
        </div>
        <span v-if="badge" class="record-badge" :class="badgeToneClass">{{ badge }}</span>
      </div>

      <div v-if="meta.length" class="record-meta">
        <span v-for="item in meta" :key="item">{{ item }}</span>
      </div>
    </div>

    <div v-if="$slots.actions" class="record-actions" @click.stop>
      <slot name="actions" />
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    title: string
    description: string
    meta?: string[]
    badge?: string
    badgeTone?: 'brand' | 'success' | 'warning' | 'danger' | 'neutral'
  }>(),
  {
    meta: () => [],
    badge: '',
    badgeTone: 'brand'
  }
)

const emit = defineEmits<{
  select: []
}>()

const badgeToneClass = computed(() => `tone-${props.badgeTone}`)
</script>

<style scoped>
.record-item {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid var(--border-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.86));
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.record-item:hover {
  transform: translateY(-1px);
  border-color: rgba(29, 78, 216, 0.18);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.record-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.record-heading h4 {
  margin: 0;
  font-size: 15px;
  line-height: 1.4;
  word-break: break-all;
}

.record-heading p {
  margin: 8px 0 0;
  color: var(--text-secondary);
  line-height: 1.6;
  font-size: 14px;
}

.record-badge,
.record-meta span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
}

.record-badge {
  border: 1px solid transparent;
  font-weight: 600;
}

.tone-brand {
  background: rgba(29, 78, 216, 0.08);
  color: var(--brand);
}

.tone-success {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.tone-warning {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.tone-danger {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.tone-neutral {
  background: rgba(148, 163, 184, 0.14);
  color: #475569;
}

.record-meta,
.record-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.record-meta span {
  background: var(--surface-muted);
  border: 1px solid var(--border-soft);
  color: var(--text-secondary);
}

@media (max-width: 960px) {
  .record-heading {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
