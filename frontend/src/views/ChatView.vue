<template>
  <div class="chat-view">
    <header class="chat-header">
      <div class="header-left">
        <div class="title-row">
          <h2 class="chat-title">智能对话</h2>
          <MembershipBadge
            v-if="authStore.username"
            :is-member="authStore.isMember"
            :membership-expires-at="authStore.membershipExpiresAt"
            size="sm"
          />
        </div>
        <p class="chat-subtitle">
          {{ authStore.isMember ? '会员专享高级编排与技能已解锁' : '普通用户模式 · 升级会员解锁更多能力' }}
        </p>
      </div>
      <div class="header-right">
        <div class="control-group">
          <label>执行模式</label>
          <el-select v-model="settingsStore.selectedMode" size="small" class="control-select">
            <el-option
              v-for="m in platformStore.executionModes"
              :key="m.key"
              :label="m.short_name"
              :value="m.key"
            />
          </el-select>
        </div>
        <div class="control-group">
          <label>模型</label>
          <el-select v-model="settingsStore.selectedProvider" size="small" class="control-select">
            <el-option
              v-for="p in providerOptions"
              :key="p.name"
              :label="providerLabel(p.name)"
              :value="p.name"
            />
          </el-select>
        </div>
        <div class="control-group">
          <label>技能</label>
          <el-select
            v-model="settingsStore.activeSkill"
            size="small"
            class="control-select"
            clearable
            placeholder="未启用"
            @change="onSkillChange"
          >
            <el-option
              v-for="s in skillOptions"
              :key="s.name"
              :label="s.display_name"
              :value="s.name"
            />
          </el-select>
        </div>
        <button class="ui-btn-ghost" @click="chatStore.clearChat()">清空当前</button>
      </div>
    </header>

    <div v-if="currentMode" class="mode-banner">
      <el-icon><Lightning /></el-icon>
      <strong>{{ currentMode.short_name }}</strong>
      <span>{{ currentMode.tagline }}</span>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-if="chatStore.messages.length === 0" class="empty-wrap">
        <EmptyState
          :title="`${platformStore.platformName}`"
          description="选择执行模式与业务技能，开始您的智能体对话"
        >
          <template #icon>
            <div class="hero-icon">
              <el-icon :size="36" color="#4F46E5"><ChatDotRound /></el-icon>
            </div>
          </template>
          <template #actions>
            <div class="mode-cards">
              <div
                v-for="m in platformStore.executionModes"
                :key="m.key"
                :class="['mode-card', { active: settingsStore.selectedMode === m.key }]"
                @click="settingsStore.selectedMode = m.key"
              >
                <div class="mode-card-title">{{ m.short_name }}</div>
                <div class="mode-card-desc">{{ m.tagline }}</div>
              </div>
            </div>
            <span class="qa-label">快捷场景</span>
            <div class="quick-row">
              <QuickChip :icon="DataAnalysis" label="财务审阅分析" @click="quickAction('analyze')" />
              <QuickChip :icon="ScaleToOriginal" label="协同决策评审" @click="quickAction('debate')" />
              <QuickChip :icon="Search" label="外部情报检索" @click="quickAction('search')" />
              <QuickChip :icon="Cpu" label="数据计算分析" @click="quickAction('code')" />
            </div>
          </template>
        </EmptyState>
      </div>

      <template v-for="msg in chatStore.messages" :key="msg.id">
        <div :class="['message', msg.role]">
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'user'"><User /></el-icon>
            <el-icon v-else-if="msg.role === 'system'"><WarningFilled /></el-icon>
            <el-icon v-else><Monitor /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-role">
              {{ msg.role === 'user' ? '我' : msg.role === 'system' ? '系统提示' : '智能体' }}
              <button
                v-if="msg.role === 'assistant' && msg.content"
                class="export-btn"
                @click="chatStore.exportMessage(msg)"
              >
                导出
              </button>
            </div>

            <div v-if="msg.thinking && msg.isStreaming" class="thinking-bar">
              <el-icon class="spin"><Loading /></el-icon>
              正在思考...
            </div>

            <div v-if="msg.steps && msg.steps.length" class="steps-timeline">
              <div v-for="(step, i) in msg.steps" :key="i" class="step-item">
                <div class="step-dot"></div>
                <div>
                  <div class="step-title">{{ stepLabel(step.title) }}</div>
                  <div v-if="step.content" class="step-content">{{ step.content }}</div>
                </div>
              </div>
            </div>

            <div v-if="msg.citations && msg.citations.length" class="citations">
              <div class="cite-label">
                <el-icon><Collection /></el-icon>
                参考来源
              </div>
              <div v-for="(c, i) in msg.citations" :key="i" class="cite-card">
                <div class="cite-title">{{ c.title }}</div>
                <div class="cite-snippet">{{ c.snippet }}</div>
              </div>
            </div>

            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>

            <div v-if="msg.tool_calls && msg.tool_calls.length > 0" class="tool-calls">
              <div v-for="(tc, i) in msg.tool_calls" :key="i" class="tool-call-item">
                <div class="tool-header">
                  <el-icon><Tools /></el-icon>
                  <span class="tool-name">{{ toolLabel(tc.tool) }}</span>
                  <span v-if="tc.result === '...'" class="tool-status running">
                    <el-icon class="spin"><Loading /></el-icon>
                    执行中
                  </span>
                  <span v-else class="tool-status done">已完成</span>
                </div>
                <details v-if="tc.result && tc.result !== '...'" class="tool-details">
                  <summary>查看详情</summary>
                  <div class="tool-result">{{ tc.result }}</div>
                </details>
              </div>
            </div>

            <span v-if="msg.isStreaming && !msg.content" class="streaming-indicator">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </span>
          </div>
        </div>
      </template>

      <div ref="scrollAnchor"></div>
    </div>

    <div class="chat-input-area">
      <div class="input-wrapper">
        <textarea
          v-model="inputText"
          @keydown="handleKeydown"
          placeholder="输入您的问题或任务描述..."
          :disabled="chatStore.isLoading"
          rows="1"
        ></textarea>
        <button
          class="btn-send"
          @click="sendMessage"
          :disabled="!inputText.trim() || chatStore.isLoading"
        >
          <el-icon><Promotion /></el-icon>
        </button>
      </div>
      <div class="input-hint">Enter 发送 · Shift+Enter 换行</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import {
  Lightning,
  Tools,
  Loading,
  Promotion,
  ChatDotRound,
  User,
  Monitor,
  WarningFilled,
  Collection,
  DataAnalysis,
  ScaleToOriginal,
  Search,
  Cpu,
} from '@element-plus/icons-vue'
import { useChatStore } from '../stores/chat'
import { useSettingsStore } from '../stores/settings'
import { usePlatformStore } from '../stores/platform'
import { useAuthStore } from '../stores/auth'
import { activateSkill, deactivateSkill, fetchSkills, fetchLLMConfig } from '../api/client'
import { toolLabel, providerLabel, stepLabel } from '../utils/displayLabels'
import MarkdownIt from 'markdown-it'
import EmptyState from '../components/ui/EmptyState.vue'
import QuickChip from '../components/ui/QuickChip.vue'
import MembershipBadge from '../components/ui/MembershipBadge.vue'

const authStore = useAuthStore()

const chatStore = useChatStore()
const settingsStore = useSettingsStore()
const platformStore = usePlatformStore()
const skillOptions = ref<any[]>([])
const providerOptions = ref<any[]>([])

const currentMode = computed(() =>
  platformStore.executionModes.find(m => m.key === settingsStore.selectedMode)
)

const inputText = ref('')
const scrollAnchor = ref<HTMLElement>()

const md = new MarkdownIt({ breaks: true, linkify: true })

function renderMarkdown(text: string): string {
  if (!text) return ''
  return md.render(text)
}

function scrollToBottom() {
  nextTick(() => {
    scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

watch(() => chatStore.messages.length, scrollToBottom)

onMounted(async () => {
  await platformStore.load()
  try {
    const data = await fetchSkills()
    skillOptions.value = data.skills || []
  } catch (e) { console.error(e) }
  try {
    const llm = await fetchLLMConfig()
    providerOptions.value = llm.providers || []
    if (llm.default_provider) settingsStore.selectedProvider = llm.default_provider
    const current = providerOptions.value.find(p => p.name === settingsStore.selectedProvider)
    if (current?.model) settingsStore.selectedModel = current.model
  } catch (e) { console.error(e) }
})

function sendMessage() {
  if (!inputText.value.trim() || chatStore.isLoading) return
  chatStore.sendMessage(inputText.value, {
    mode: settingsStore.selectedMode,
    skill: settingsStore.activeSkill,
    provider: settingsStore.selectedProvider,
    model: settingsStore.selectedModel || null,
  })
  inputText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

async function onSkillChange() {
  if (settingsStore.activeSkill) {
    await activateSkill(settingsStore.activeSkill)
  } else {
    await deactivateSkill()
  }
}

function quickAction(type: string) {
  switch (type) {
    case 'analyze':
      settingsStore.activeSkill = 'financial_audit'
      activateSkill('financial_audit').catch(console.error)
      inputText.value = '请分析以下财务数据并给出审阅意见'
      break
    case 'debate':
      settingsStore.selectedMode = 'collaborative_decision'
      inputText.value = '请对目标公司进行多视角协同决策分析'
      break
    case 'search':
      inputText.value = '检索人工智能领域的最新行业动态，并总结关键趋势'
      break
    case 'code':
      inputText.value = '计算 1 万元本金按 5% 年利率复利 20 年的最终金额'
      break
  }
}
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(199, 210, 254, 0.4);
  gap: 16px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.chat-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #1E1B4B, #6366F1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mode-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 24px;
  background: linear-gradient(90deg, rgba(238,242,255,0.9), rgba(236,254,255,0.6));
  border-bottom: 1px solid rgba(199, 210, 254, 0.35);
  font-size: 13px;
  color: var(--ui-text-regular);
  flex-shrink: 0;
}

.mode-card {
  cursor: pointer;
  padding: 14px 16px;
  text-align: left;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(199, 210, 254, 0.45);
  border-radius: 12px;
  transition: all 0.22s ease;
  position: relative;
  overflow: hidden;
}

.mode-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--gradient-accent);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.mode-card:hover {
  border-color: rgba(129, 140, 248, 0.55);
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(99, 102, 241, 0.12);
}

.mode-card:hover::before { opacity: 0.5; }

.mode-card.active {
  border-color: rgba(99, 102, 241, 0.55);
  background: linear-gradient(145deg, rgba(238,242,255,0.95), rgba(236,254,255,0.7));
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.15);
}

.mode-card.active::before { opacity: 1; }

.hero-icon {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(238,242,255,0.95), rgba(236,254,255,0.8));
  border: 1px solid rgba(199, 210, 254, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.15);
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(199, 210, 254, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--color-violet);
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.08);
}

.message.user .message-avatar {
  background: var(--gradient-primary);
  border: none;
  color: #fff;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.message-content {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  padding: 12px 16px;
  border: 1px solid rgba(199, 210, 254, 0.4);
  min-width: 0;
  flex: 1;
  box-shadow: 0 2px 12px rgba(99, 102, 241, 0.06);
}

.message.user .message-content {
  background: var(--gradient-primary);
  border: none;
  color: #fff;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25);
}

.tool-call-item {
  background: linear-gradient(135deg, rgba(238,242,255,0.7), rgba(236,254,255,0.5));
  border-radius: 10px;
  padding: 8px 12px;
  border: 1px solid rgba(199, 210, 254, 0.4);
}

.chat-input-area {
  padding: 12px 24px 20px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(16px);
  border-top: 1px solid rgba(199, 210, 254, 0.4);
  flex-shrink: 0;
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(199, 210, 254, 0.5);
  border-radius: 14px;
  padding: 8px 10px 8px 16px;
  transition: all 0.22s ease;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.08);
}

.input-wrapper:focus-within {
  border-color: rgba(99, 102, 241, 0.55);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15);
}

.btn-send {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--btn-primary-bg);
  border: none;
  color: var(--btn-primary-color);
  cursor: pointer;
  transition: all 0.22s ease;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  box-shadow: var(--btn-primary-shadow);
}

.btn-send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--btn-primary-hover-shadow);
}

.steps-timeline {
  margin-bottom: 10px;
  padding-left: 8px;
  border-left: 2px solid rgba(129, 140, 248, 0.4);
}

.cite-card {
  background: linear-gradient(135deg, rgba(245,243,255,0.8), rgba(238,242,255,0.6));
  border-radius: 10px;
  padding: 8px 12px;
  margin-bottom: 6px;
  border: 1px solid rgba(199, 210, 254, 0.4);
}

.header-left { min-width: 0; }
.chat-subtitle { font-size: 13px; color: var(--ui-text-secondary); margin: 4px 0 0; }
.mode-banner strong { color: var(--color-primary); }
.header-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.control-group { display: flex; align-items: center; gap: 6px; }
.control-group label { font-size: 12px; color: var(--ui-text-secondary); white-space: nowrap; }
.control-select { width: 120px; }
.mode-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; max-width: 640px; width: 100%; }
.mode-card-title { font-size: 13px; font-weight: 600; color: var(--ui-text-primary); margin-bottom: 4px; }
.mode-card-desc { font-size: 11px; color: var(--ui-text-secondary); }
.qa-label { display: block; width: 100%; font-size: 12px; color: var(--color-violet); margin: 16px 0 8px; font-weight: 600; }
.quick-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.empty-wrap { height: 100%; display: flex; align-items: center; justify-content: center; }
.chat-messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; }
.message { display: flex; gap: 12px; max-width: 780px; }
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message.user .message-role, .message.user .message-text { color: rgba(255, 255, 255, 0.95); }
.message.system .message-content { background: #FEF2F2; border-color: #FECACA; }
.message-role { font-size: 12px; color: var(--ui-text-secondary); margin-bottom: 6px; font-weight: 600; }
.message-text { font-size: 14px; line-height: 1.7; color: var(--ui-text-primary); word-break: break-word; }
.message-text :deep(pre) { background: var(--ui-bg-muted); padding: 12px; border-radius: 8px; overflow-x: auto; font-size: 13px; margin: 8px 0; }
.message-text :deep(code) { font-size: 13px; background: var(--ui-bg-muted); padding: 2px 6px; border-radius: 4px; }
.message-text :deep(pre code) { background: none; padding: 0; }
.tool-calls { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
.tool-header { display: flex; align-items: center; gap: 6px; color: var(--ui-text-primary); }
.tool-name { font-size: 13px; font-weight: 600; flex: 1; }
.tool-status { font-size: 11px; display: inline-flex; align-items: center; gap: 4px; }
.tool-status.running { color: var(--ui-warning); }
.tool-status.done { color: var(--ui-success); }
.tool-details { margin-top: 6px; }
.tool-details summary { font-size: 12px; color: var(--ui-text-secondary); cursor: pointer; user-select: none; }
.tool-result { margin-top: 6px; font-size: 12px; color: var(--ui-text-regular); white-space: pre-wrap; max-height: 160px; overflow-y: auto; padding: 8px; background: rgba(255,255,255,0.8); border-radius: 6px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.streaming-indicator { display: inline-flex; gap: 4px; padding: 4px 0; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-primary); animation: pulse 1.4s infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }
.input-wrapper textarea { flex: 1; padding: 6px 0; background: transparent; border: none; color: var(--ui-text-primary); font-size: 14px; resize: none; outline: none; font-family: var(--ui-font); line-height: 1.5; max-height: 120px; }
.input-wrapper textarea::placeholder { color: var(--text-placeholder); }
.btn-send:disabled { opacity: 0.45; cursor: not-allowed; }
.input-hint { text-align: center; font-size: 11px; color: var(--ui-text-secondary); margin-top: 6px; }
.thinking-bar { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-primary); margin-bottom: 8px; }
.step-item { display: flex; gap: 10px; margin-bottom: 8px; }
.step-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-primary); margin-top: 6px; flex-shrink: 0; }
.step-title { font-size: 12px; font-weight: 600; color: var(--ui-text-primary); }
.step-content { font-size: 12px; color: var(--ui-text-regular); margin-top: 2px; }
.citations { margin-bottom: 10px; }
.cite-label { font-size: 12px; font-weight: 600; margin-bottom: 6px; color: var(--ui-text-primary); display: flex; align-items: center; gap: 4px; }
.cite-title { font-size: 12px; font-weight: 600; }
.cite-snippet { font-size: 12px; color: var(--ui-text-regular); margin-top: 4px; line-height: 1.5; }
.export-btn { float: right; font-size: 11px; padding: 2px 8px; border: 1px solid var(--btn-ghost-border); border-radius: 6px; background: var(--btn-ghost-bg); cursor: pointer; color: var(--btn-ghost-color); }
.export-btn:hover { color: var(--btn-ghost-hover-color); border-color: var(--btn-ghost-hover-border); background: var(--btn-ghost-hover-bg); }
</style>
