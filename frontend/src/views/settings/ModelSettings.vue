<template>
  <div class="settings-panel model-panel">
    <SettingsBackBar />

    <GlassCard v-if="!auth.isMember" class="upgrade-banner">
      <div class="upgrade-content">
        <el-icon :size="20"><Warning /></el-icon>
        <div>
          <strong>升级会员后可配置个人模型接入</strong>
          <p>普通用户仅可查看平台默认模型配置，会员可自定义 API Key 与模型参数。</p>
        </div>
      </div>
      <router-link to="/membership" class="ui-btn-primary upgrade-btn">了解会员</router-link>
    </GlassCard>

    <GlassCard v-if="systemStatus" class="status-card">
      <h3 class="section-title">运行状态</h3>
      <div class="status-grid">
        <el-tag :type="tagType(systemStatus.chroma?.status)">
          向量知识库：{{ statusText(systemStatus.chroma?.status) }}
        </el-tag>
        <el-tag :type="tagType(systemStatus.neo4j?.status)">
          知识图谱：{{ statusText(systemStatus.neo4j?.status) }}
        </el-tag>
        <el-tag :type="tagType(systemStatus.llm?.status)">
          模型服务：{{ statusText(systemStatus.llm?.status) }}
        </el-tag>
      </div>
      <div class="default-row">
        <span class="default-label">默认模型接入</span>
        <el-select
          v-model="defaultProvider"
          class="default-select"
          :disabled="!canEdit"
          @change="onDefaultChange"
        >
          <el-option
            v-for="p in providers"
            :key="p.name"
            :label="providerLabel(p.name)"
            :value="p.name"
          />
        </el-select>
      </div>
    </GlassCard>

    <div class="providers">
      <GlassCard v-for="p in providers" :key="p.name" class="provider-card">
        <div class="provider-header">
          <div class="provider-info">
            <div class="provider-icon">
              <el-icon :size="20"><component :is="providerIcon(p.name)" /></el-icon>
            </div>
            <div>
              <h4>{{ providerLabel(p.name) }}</h4>
              <span class="provider-desc">{{ providerDesc(p.name) }}</span>
            </div>
          </div>
          <el-tag type="primary" effect="plain" round>
            {{ configs[p.name]?.model || p.model }}
          </el-tag>
          <el-tag v-if="p.has_api_key" size="small" type="success" effect="plain">Key 已配置</el-tag>
          <el-tag v-else size="small" type="info" effect="plain">Key 未配置</el-tag>
        </div>

        <GradientDivider spacing="0 0 16px" />

        <div class="form-row">
          <label>API 密钥</label>
          <el-input
            v-if="canEdit"
            v-model="configs[p.name].api_key"
            type="password"
            placeholder="请输入 API Key"
            show-password
          />
          <el-input v-else model-value="******" disabled />
        </div>

        <div class="form-row" v-if="p.name !== 'anthropic'">
          <label>网关地址</label>
          <el-input
            v-model="configs[p.name].base_url"
            placeholder="https://api.openai.com/v1"
            :disabled="!canEdit"
          />
        </div>

        <div class="form-row">
          <label>模型名称</label>
          <el-input
            v-model="configs[p.name].model"
            placeholder="例如 gpt-4o"
            :disabled="!canEdit"
          />
        </div>

        <div class="form-row">
          <label>采样温度</label>
          <div class="range-row">
            <el-slider
              v-model="configs[p.name].temperature"
              :min="0"
              :max="2"
              :step="0.1"
              show-input
              :disabled="!canEdit"
            />
          </div>
        </div>

        <button
          v-if="canEdit"
          class="ui-btn-primary save-btn"
          @click="saveProvider(p.name)"
        >
          保存 {{ providerLabel(p.name) }} 配置
        </button>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Cloudy, Cpu, House, Warning } from '@element-plus/icons-vue'
import { fetchLLMConfig, updateLLMConfig, setDefaultProvider, fetchSystemStatus } from '../../api/client'
import { useAuthStore } from '../../stores/auth'
import GlassCard from '../../components/ui/GlassCard.vue'
import GradientDivider from '../../components/ui/GradientDivider.vue'
import SettingsBackBar from '../../components/settings/SettingsBackBar.vue'
import { providerLabel as catalogProviderLabel } from '../../utils/displayLabels'

const auth = useAuthStore()
const canEdit = computed(() => auth.isMember)

const providers = ref<any[]>([])
const systemStatus = ref<any>(null)
const defaultProvider = ref('deepseek')
const configs = reactive<Record<string, any>>({})

const labelMap: Record<string, string> = {
  deepseek: 'DeepSeek',
  openai: 'OpenAI 兼容接口',
  anthropic: 'Anthropic Claude',
  custom: '私有化模型网关',
}
const descMap: Record<string, string> = {
  deepseek: 'DeepSeek 官方 API，OpenAI 兼容协议',
  openai: '适用于 OpenAI 官方及 OneAPI、Azure OpenAI 等兼容网关',
  anthropic: '适用于 Anthropic 官方 API',
  custom: '适用于 Ollama、vLLM、LocalAI 等本地或私有部署',
}
const iconMap: Record<string, typeof Connection> = {
  deepseek: Connection,
  openai: Cloudy,
  anthropic: Cpu,
  custom: House,
}

function providerLabel(name: string) {
  const p = providers.value.find((x) => x.name === name)
  return p?.display_name || catalogProviderLabel(name) || labelMap[name] || name
}
function providerDesc(name: string) {
  return descMap[name] || ''
}
function providerIcon(name: string) {
  return iconMap[name] || Connection
}

function statusText(s: string) {
  if (s === 'up') return '正常'
  if (s === 'down') return '不可用'
  return '未知'
}

function tagType(s: string) {
  if (s === 'up') return 'success'
  if (s === 'down') return 'danger'
  return 'warning'
}

onMounted(async () => {
  try {
    const data = await fetchLLMConfig()
    providers.value = data.providers || []
    defaultProvider.value = data.default_provider || 'deepseek'
    for (const p of providers.value) {
      configs[p.name] = {
        api_key: '',
        base_url: p.base_url || '',
        model: p.model || '',
        temperature: p.temperature ?? 0.7,
      }
    }
    systemStatus.value = await fetchSystemStatus()
  } catch (e) {
    console.error(e)
  }
})

async function onDefaultChange() {
  if (!canEdit.value) return
  try {
    await setDefaultProvider(defaultProvider.value)
    ElMessage.success('默认模型已更新')
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  }
}

async function saveProvider(name: string) {
  if (!canEdit.value) return
  try {
    await updateLLMConfig(name, {
      api_key: configs[name].api_key || undefined,
      base_url: configs[name].base_url || undefined,
      model: configs[name].model || undefined,
      temperature: configs[name].temperature,
    })
    ElMessage.success(`已保存「${providerLabel(name)}」配置`)
  } catch (e: any) {
    const msg = e.response?.status === 403
      ? '升级会员后可配置个人模型接入'
      : `保存失败：${e.message}`
    ElMessage.error(msg)
  }
}
</script>

<style scoped>
.model-panel {
  max-width: 820px;
}

.upgrade-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  border-color: var(--upgrade-banner-border) !important;
  background: var(--upgrade-banner-bg) !important;
}

.upgrade-content {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  color: var(--upgrade-banner-text);
}

.upgrade-content strong {
  display: block;
  margin-bottom: 4px;
  font-size: 14px;
}

.upgrade-content p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  opacity: 0.9;
}

.upgrade-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 96px;
  height: 40px;
  padding: 0 16px;
  text-decoration: none;
  white-space: nowrap;
  line-height: 1;
  text-align: center;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
}

.status-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.default-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.default-label {
  font-size: 13px;
  color: var(--ui-text-regular);
  white-space: nowrap;
}

.default-select {
  width: 220px;
}

.providers {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.provider-info {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.provider-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--ui-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.provider-header h4 {
  font-size: 15px;
  font-weight: bold;
  margin-bottom: 4px;
}

.provider-desc {
  font-size: 12px;
  color: var(--ui-text-secondary);
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.form-row label {
  width: 72px;
  font-size: 13px;
  color: var(--ui-text-regular);
  flex-shrink: 0;
  font-weight: 600;
}

.form-row .el-input,
.range-row {
  flex: 1;
}

.save-btn {
  margin-top: 4px;
}
</style>
