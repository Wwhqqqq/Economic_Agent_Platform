<template>
  <div class="settings-panel">
    <SettingsBackBar />
    <GlassCard>
      <h3 class="panel-title">主题模式</h3>
      <p class="panel-desc">选择界面配色方案，立即生效并保存在本设备。</p>

      <div class="theme-options">
        <button
          v-for="opt in themeOptions"
          :key="opt.value"
          type="button"
          :class="['theme-card', { active: themeMode === opt.value }]"
          @click="selectTheme(opt.value)"
        >
          <div :class="['theme-preview', opt.value]" />
          <span class="theme-label">{{ opt.label }}</span>
          <span class="theme-hint">{{ opt.hint }}</span>
        </button>
      </div>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">语言</h3>
      <p class="panel-desc">界面语言设置（即将推出）</p>
      <el-select model-value="zh-CN" disabled class="lang-select">
        <el-option label="简体中文" value="zh-CN" />
        <el-option label="English" value="en" />
      </el-select>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GlassCard from '../../components/ui/GlassCard.vue'
import SettingsBackBar from '../../components/settings/SettingsBackBar.vue'
import { getThemeMode, setThemeMode, type ThemeMode } from '../../utils/theme'

const themeMode = ref<ThemeMode>('light')

const themeOptions: { value: ThemeMode; label: string; hint: string }[] = [
  { value: 'light', label: '浅色', hint: '明亮清爽' },
  { value: 'dark', label: '深色', hint: '护眼沉浸' },
  { value: 'system', label: '跟随系统', hint: '自动切换' },
]

function selectTheme(mode: ThemeMode) {
  themeMode.value = mode
  setThemeMode(mode)
}

onMounted(() => {
  themeMode.value = getThemeMode()
})
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 720px;
}

.panel-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ui-text-primary);
}

.panel-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--ui-text-secondary);
}

.theme-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.theme-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 14px 10px;
  border-radius: 12px;
  border: 1px solid var(--theme-card-border);
  background: var(--theme-card-bg);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: var(--ui-font);
}

.theme-card:hover {
  border-color: var(--btn-ghost-hover-border);
  box-shadow: var(--btn-ghost-hover-shadow);
}

.theme-card.active {
  border-color: var(--color-primary);
  background: var(--theme-card-active-bg);
  box-shadow: var(--theme-card-active-shadow);
}

.theme-preview {
  width: 100%;
  height: 48px;
  border-radius: 8px;
  border: 1px solid rgba(199, 210, 254, 0.45);
}

.theme-preview.light {
  background: linear-gradient(135deg, #f5f3ff, #eef2ff);
}

.theme-preview.dark {
  background: linear-gradient(135deg, #1e1b4b, #312e81);
}

.theme-preview.system {
  background: linear-gradient(90deg, #eef2ff 50%, #1e1b4b 50%);
}

.theme-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ui-text-primary);
}

.theme-hint {
  font-size: 11px;
  color: var(--ui-text-secondary);
}

.lang-select {
  width: 220px;
}

@media (max-width: 768px) {
  .theme-options {
    grid-template-columns: 1fr;
  }
}
</style>
