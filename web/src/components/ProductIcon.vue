<template>
  <span class="product-icon" :class="[`icon-${name}`, { spinning }]" aria-hidden="true">
    <svg v-if="name === 'upload-panel'" viewBox="0 0 64 64" fill="none">
      <rect x="10" y="12" width="44" height="40" rx="14" class="stroke-main" />
      <path d="M21 39h22" class="stroke-main" />
      <path d="M32 23v18" class="stroke-main" />
      <path d="m24 31 8-8 8 8" class="stroke-main" />
    </svg>
    <svg v-else-if="name === 'spinner'" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="18" class="stroke-muted" />
      <path d="M32 14a18 18 0 0 1 18 18" class="stroke-main" />
    </svg>
    <svg v-else-if="name === 'health-ok'" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="21" class="stroke-main" />
      <path d="m23 32 6 6 12-13" class="stroke-main" />
    </svg>
    <svg v-else-if="name === 'health-error'" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="21" class="stroke-main" />
      <path d="m25 25 14 14" class="stroke-main" />
      <path d="m39 25-14 14" class="stroke-main" />
    </svg>
    <svg v-else-if="name === 'health-idle'" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="21" class="stroke-main" />
      <path d="M32 27v10" class="stroke-main" />
      <circle cx="32" cy="42" r="1.5" class="fill-main" />
    </svg>
    <svg v-else-if="name === 'refresh'" viewBox="0 0 64 64" fill="none">
      <path d="M47 29a15 15 0 1 1-4-10" class="stroke-main" />
      <path d="M47 18v11H36" class="stroke-main" />
    </svg>
    <svg v-else-if="name === 'info'" viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="21" class="stroke-main" />
      <path d="M32 29v12" class="stroke-main" />
      <circle cx="32" cy="22" r="1.5" class="fill-main" />
    </svg>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  name:
    | 'upload-panel'
    | 'spinner'
    | 'health-ok'
    | 'health-error'
    | 'health-idle'
    | 'refresh'
    | 'info'
  spinning?: boolean
}>()
</script>

<style scoped>
.product-icon {
  display: inline-flex;
  width: 1em;
  height: 1em;
}

.product-icon svg {
  width: 100%;
  height: 100%;
}

.stroke-main,
.stroke-muted {
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 3;
}

.stroke-main {
  stroke: currentColor;
}

.stroke-muted {
  stroke: rgba(148, 163, 184, 0.35);
}

.fill-main {
  fill: currentColor;
}

.spinning {
  animation: product-spin 1s linear infinite;
}

@keyframes product-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
