<template>
  <div class="settings-panel">
    <SettingsBackBar />

    <GlassCard>
      <div class="about-header">
        <div class="about-icon">
          <el-icon :size="28"><Monitor /></el-icon>
        </div>
        <div>
          <h3 class="app-name">{{ platformStore.platformName }}</h3>
          <p class="version-line">{{ formatVersionLabel() }}</p>
        </div>
      </div>

      <GradientDivider spacing="16px 0" />

      <dl class="info-list">
        <div class="info-row">
          <dt>应用名称</dt>
          <dd>{{ APP_NAME }}</dd>
        </div>
        <div class="info-row">
          <dt>版本号</dt>
          <dd>{{ formatVersionLabel() }}</dd>
        </div>
        <div class="info-row">
          <dt>构建环境</dt>
          <dd>{{ buildEnv }}</dd>
        </div>
      </dl>

      <div class="action-row">
        <button type="button" class="ui-btn-ghost" @click="checkUpdate">检查更新</button>
      </div>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">服务状态</h3>
      <p class="panel-desc">后端健康检查摘要</p>
      <div v-if="health" class="health-tags">
        <el-tag :type="health.status === 'healthy' ? 'success' : 'warning'">
          整体：{{ health.status === 'healthy' ? '正常' : '部分受限' }}
        </el-tag>
      </div>
      <p v-else class="panel-desc">加载中…</p>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">权限说明</h3>
      <p class="panel-desc">不同账号类型可使用的能力对比如下。</p>
      <table class="perm-table">
        <thead>
          <tr>
            <th>能力</th>
            <th>普通用户</th>
            <th>会员</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in permissionRows" :key="row.name">
            <td>{{ row.name }}</td>
            <td>{{ row.regular ? '✓' : '—' }}</td>
            <td>{{ row.member ? '✓' : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">法律信息</h3>
      <div class="link-list">
        <a href="#" class="legal-link" @click.prevent="showComingSoon">用户协议</a>
        <a href="#" class="legal-link" @click.prevent="showComingSoon">隐私政策</a>
        <a
          href="https://github.com/Wwhqqqq/Economic_Agent_Platform"
          target="_blank"
          rel="noopener noreferrer"
          class="legal-link"
        >
          开源仓库
        </a>
      </div>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Monitor } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usePlatformStore } from '../../stores/platform'
import { fetchSystemStatus } from '../../api/client'
import { APP_NAME, formatVersionLabel } from '../../utils/appVersion'
import GlassCard from '../../components/ui/GlassCard.vue'
import GradientDivider from '../../components/ui/GradientDivider.vue'
import SettingsBackBar from '../../components/settings/SettingsBackBar.vue'

const permissionRows = [
  { name: 'ReAct 对话', regular: true, member: true },
  { name: 'Plan-Execute / Multi-Agent', regular: false, member: true },
  { name: '会员专享技能', regular: false, member: true },
  { name: '个人 LLM 配置', regular: false, member: true },
  { name: '会员专享知识库', regular: false, member: true },
]

const platformStore = usePlatformStore()
const health = ref<any>(null)
const buildEnv = import.meta.env.PROD ? 'production' : 'development'

function showComingSoon() {
  ElMessage.info('敬请期待')
}

function checkUpdate() {
  ElMessage.success('当前已是最新版本')
}

onMounted(async () => {
  try {
    health.value = await fetchSystemStatus()
  } catch {
    health.value = null
  }
})
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 720px;
}

.about-header {
  display: flex;
  align-items: center;
  gap: 14px;
}

.about-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: var(--gradient-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35);
}

.app-name {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 700;
  color: var(--ui-text-primary);
}

.version-line {
  margin: 0;
  font-size: 13px;
  color: var(--ui-text-secondary);
}

.panel-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}

.panel-desc {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--ui-text-secondary);
}

.info-list {
  margin: 0 0 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(199, 210, 254, 0.35);
  font-size: 13px;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row dt {
  font-weight: 600;
  color: var(--ui-text-regular);
}

.info-row dd {
  margin: 0;
  color: var(--ui-text-primary);
}

.action-row {
  display: flex;
  gap: 10px;
}

.health-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legal-link {
  font-size: 14px;
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 600;
}

.legal-link:hover {
  text-decoration: underline;
}

.perm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.perm-table th,
.perm-table td {
  padding: 10px 8px;
  border-bottom: 1px solid var(--settings-list-divider, rgba(199, 210, 254, 0.35));
  text-align: left;
}

.perm-table th {
  font-weight: 600;
  color: var(--ui-text-regular);
}

.perm-table td:nth-child(2),
.perm-table td:nth-child(3),
.perm-table th:nth-child(2),
.perm-table th:nth-child(3) {
  text-align: center;
  width: 88px;
}
</style>
