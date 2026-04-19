<template>
  <div class="section-head">
    <div>
      <p class="title">{{ title }}</p>
      <p class="caption">{{ caption }}</p>
    </div>
    <div class="head-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  caption: string
}>()
</script>

<style scoped>
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.caption {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .section-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
