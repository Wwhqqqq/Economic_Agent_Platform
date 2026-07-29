<template>
  <div class="page-shell">
    <PageHeader
      title="设置"
      subtitle="管理账号、偏好、模型接入与应用信息"
      breadcrumb="系统 / 设置"
    />

    <div class="page-body">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import PageHeader from '../components/layout/PageHeader.vue'
</script>

<style scoped>
.page-body {
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.page-body :deep(.settings-index),
.page-body :deep(.settings-panel) {
  width: 100%;
  max-width: var(--settings-content-width, 720px);
}
</style>
