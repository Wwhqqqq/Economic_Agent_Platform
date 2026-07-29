<template>
  <nav class="settings-back">
    <router-link to="/settings" class="back-link">
      <el-icon><ArrowLeft /></el-icon>
      <span>返回设置</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
</script>

<style scoped>
.settings-back {
  margin-bottom: 14px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  text-decoration: none;
  padding: 6px 0;
}

.back-link:hover {
  color: var(--color-primary-hover);
}
</style>
