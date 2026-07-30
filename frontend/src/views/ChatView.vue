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
    </header>

    <div v-if="settingsStore.activeExpertName" class="context-banner">
      <el-icon><User /></el-icon>
      <strong>{{ settingsStore.activeExpertName }}</strong>
      <span>已召唤，请描述您的任务</span>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-if="chatStore.messages.length === 0" class="empty-wrap">
        <EmptyState
          :title="`${platformStore.platformName}`"
          description="输入 / 召唤技能，或从专家中心召唤领域专家"
        >
          <template #icon>
            <div class="hero-icon">
              <el-icon :size="36" color="#4F46E5"><ChatDotRound /></el-icon>
            </div>
          </template>
          <template #actions>
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
            <span v-if="msg.isStreaming && msg.content" class="stream-cursor" aria-hidden="true">▍</span>

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
      <div class="composer-bar">
        <div class="mode-select-wrap">
          <el-select
            v-model="selectedMode"
            size="small"
            class="mode-select"
            popper-class="mode-select-popper"
          >
            <el-option
              v-for="m in executionModeOptions"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            >
              <div class="mode-option">
                <span class="mode-option-label">{{ m.label }}</span>
                <span class="mode-option-desc">{{ m.desc }}</span>
              </div>
            </el-option>
          </el-select>
        </div>
      </div>
      <div v-if="settingsStore.activeExpertName || settingsStore.activeSkill" class="context-chips">
        <span v-if="settingsStore.activeExpertName" class="ctx-chip expert">
          {{ settingsStore.activeExpertName }}
          <button type="button" class="chip-x" @click="clearExpert">×</button>
        </span>
        <span v-if="settingsStore.activeSkill" class="ctx-chip skill">
          {{ settingsStore.activeSkillLabel || settingsStore.activeSkill }}
          <button type="button" class="chip-x" @click="clearSkill">×</button>
        </span>
      </div>
      <div class="input-shell">
        <AttachmentUpload
          ref="attachmentRef"
          :disabled="chatStore.isLoading"
          @update="onAttachmentsUpdate"
        />
        <SlashSkillMenu
          ref="slashMenuRef"
          :visible="slashMenuVisible"
          :query="slashQuery"
          :skills="invocableSkills"
          @select="onSlashSelect"
          @close="slashMenuVisible = false"
        />
        <div class="input-wrapper">
          <textarea
            ref="textareaRef"
            v-model="inputText"
            @keydown="handleKeydown"
            @input="onInputChange"
            :placeholder="inputPlaceholder"
            :disabled="chatStore.isLoading"
            rows="1"
          ></textarea>
          <button
            class="btn-send"
            @click="sendMessage"
            :disabled="!canSend || chatStore.isLoading"
          >
            <el-icon><Promotion /></el-icon>
          </button>
        </div>
      </div>
      <div class="input-hint">Enter 发送 · Shift+Enter 换行 · 输入 <code>/</code> 召唤技能 · 可拖入图片</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import {
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
import { usePlatformStore } from '../stores/platform'
import { useAuthStore } from '../stores/auth'
import { fetchExperts, fetchInvocableSkills, fetchLLMConfig } from '../api/client'
import { toolLabel, stepLabel } from '../utils/displayLabels'
import { parseSlashCommand, slashQueryFromInput } from '../utils/slashCommand'
import MarkdownIt from 'markdown-it'
import EmptyState from '../components/ui/EmptyState.vue'
import QuickChip from '../components/ui/QuickChip.vue'
import MembershipBadge from '../components/ui/MembershipBadge.vue'
import SlashSkillMenu, { type InvocableSkill } from '../components/chat/SlashSkillMenu.vue'
import AttachmentUpload, { type AttachmentItem } from '../components/chat/AttachmentUpload.vue'
import { useSettingsStore } from '../stores/settings'

const authStore = useAuthStore()
const route = useRoute()

const chatStore = useChatStore()
const settingsStore = useSettingsStore()
const { selectedMode } = storeToRefs(settingsStore)
const platformStore = usePlatformStore()

const invocableSkills = ref<InvocableSkill[]>([])

const executionModeOptions = [
  { label: 'Auto', value: 'adaptive', desc: '自动模式' },
  { label: 'Medium', value: 'reasoning_action', desc: '推理闭环' },
  { label: 'Plan', value: 'task_orchestration', desc: '任务编排' },
]

const slashMenuVisible = ref(false)
const slashMenuRef = ref<InstanceType<typeof SlashSkillMenu> | null>(null)
const textareaRef = ref<HTMLTextAreaElement>()

const inputText = ref('')
const scrollAnchor = ref<HTMLElement>()

const slashQuery = computed(() => slashQueryFromInput(inputText.value))

const inputPlaceholder = computed(() =>
  settingsStore.activeExpertName
    ? `向${settingsStore.activeExpertName}描述您的任务…`
    : '输入您的问题，或 / 召唤技能…'
)

const attachmentRef = ref<InstanceType<typeof AttachmentUpload> | null>(null)
const pendingAttachments = ref<AttachmentItem[]>([])

const canSend = computed(() => {
  const { skill, message } = parseSlashCommand(inputText.value)
  if (skill) return message.trim().length > 0
  return inputText.value.trim().length > 0 || pendingAttachments.value.length > 0
})

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

watch(
  () => chatStore.messages.filter(m => m.isStreaming).map(m => m.content).join('\n'),
  scrollToBottom,
)

onMounted(async () => {
  await platformStore.load()
  try {
    const llm = await fetchLLMConfig()
    if (llm.default_provider) settingsStore.selectedProvider = llm.default_provider
    const current = (llm.providers || []).find((p: { name: string }) => p.name === settingsStore.selectedProvider)
    if (current?.model) settingsStore.selectedModel = current.model
  } catch (e) { console.error(e) }
  try {
    const data = await fetchInvocableSkills()
    invocableSkills.value = data.skills || []
  } catch (e) { console.error(e) }
  await applyRouteSummon()
})

watch(() => route.query, applyRouteSummon)

async function applyRouteSummon() {
  await settingsStore.syncFromBackend(chatStore.sessionId)
  const summonId = route.query.summon as string | undefined
  if (!summonId) return
  try {
    const data = await fetchExperts()
    const all = [...(data.experts || []), ...(data.teams || [])]
    const profile = all.find((p: any) => p.id === summonId)
    if (profile) {
      await settingsStore.summonExpert(profile, chatStore.sessionId)
    }
  } catch (e) { console.error(e) }
  const prompt = route.query.prompt as string | undefined
  if (prompt) inputText.value = prompt
}

function onInputChange() {
  slashMenuVisible.value = inputText.value.startsWith('/')
}

function onSlashSelect(skill: InvocableSkill) {
  settingsStore.setActiveSkill(skill.name, skill.display_name, 'slash')
  inputText.value = `${skill.slash_command} `
  slashMenuVisible.value = false
  nextTick(() => textareaRef.value?.focus())
}

function applySlash(name: string) {
  const skill = invocableSkills.value.find(s => s.name === name)
  settingsStore.setActiveSkill(name, skill?.display_name || name, 'slash')
  inputText.value = `/${name} `
  textareaRef.value?.focus()
}

async function clearSkill() {
  await settingsStore.clearSkill(chatStore.sessionId)
  await chatStore.sendContextClear({ clear_skill: true })
}

async function clearExpert() {
  await settingsStore.clearExpert(chatStore.sessionId)
  await chatStore.sendContextClear({ clear_expert: true })
}

function onAttachmentsUpdate(items: AttachmentItem[]) {
  pendingAttachments.value = items
}

function sendMessage() {
  if (!canSend.value || chatStore.isLoading) return

  const parsed = parseSlashCommand(inputText.value)
  let message = inputText.value
  let skill = settingsStore.activeSkill
  let skillInvocation = settingsStore.skillInvocationSource

  if (parsed.skill) {
    if (!parsed.message.trim()) return
    message = parsed.message
    skill = parsed.skill
    skillInvocation = 'slash'
    const meta = invocableSkills.value.find(s => s.name === parsed.skill)
    settingsStore.setActiveSkill(parsed.skill, meta?.display_name || parsed.skill, 'slash')
  }

  chatStore.sendMessage(message, {
    mode: selectedMode.value,
    skill,
    expert_id: settingsStore.activeExpertId,
    skill_invocation: skillInvocation,
    provider: settingsStore.selectedProvider,
    model: settingsStore.selectedModel || null,
    attachments: pendingAttachments.value.map(a => ({
      asset_id: a.asset_id,
      url: a.data_url || a.url,
      data_url: a.data_url,
      ocr_text: a.ocr_text,
      vlm_caption: a.vlm_caption,
      caption: a.vlm_caption,
      filename: a.filename,
    })),
  })
  inputText.value = ''
  slashMenuVisible.value = false
  attachmentRef.value?.clear()
  pendingAttachments.value = []
}

function handleKeydown(e: KeyboardEvent) {
  if (slashMenuVisible.value && slashMenuRef.value) {
    if (e.key === 'ArrowDown') { e.preventDefault(); slashMenuRef.value.move(1); return }
    if (e.key === 'ArrowUp') { e.preventDefault(); slashMenuRef.value.move(-1); return }
    if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey && slashQuery.value && !canSend.value)) {
      e.preventDefault()
      slashMenuRef.value.confirm()
      return
    }
    if (e.key === 'Escape') { slashMenuVisible.value = false; return }
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function quickAction(type: string) {
  switch (type) {
    case 'analyze':
      applySlash('financial_audit')
      inputText.value = '/financial_audit 请分析以下财务数据并给出审阅意见'
      break
    case 'debate':
      settingsStore.summonExpert({
        id: 'finance_review_board',
        name: '财务评审委员会',
        equipped_skills: [],
      })
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

.context-banner {
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

.context-banner strong { color: var(--color-primary); }

.composer-bar {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.mode-select-wrap {
  display: inline-flex;
}

.mode-select {
  width: 108px;
}

.mode-select :deep(.el-select__wrapper) {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 1px 4px rgba(99, 102, 241, 0.08);
  font-weight: 600;
  font-size: 12px;
}

.mode-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 0;
}

.mode-option-label {
  font-size: 13px;
  font-weight: 600;
}

.mode-option-desc {
  font-size: 11px;
  color: var(--ui-text-secondary);
}

.context-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.ctx-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(238, 242, 255, 0.95);
  border: 1px solid rgba(199, 210, 254, 0.5);
  color: var(--color-primary);
}

.ctx-chip.expert { color: #4338ca; }
.chip-x {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  color: inherit;
  opacity: 0.7;
  padding: 0;
}
.chip-x:hover { opacity: 1; }

.input-shell {
  position: relative;
}

.input-hint code {
  font-size: 11px;
  background: rgba(238, 242, 255, 0.8);
  padding: 1px 4px;
  border-radius: 4px;
}

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
.stream-cursor {
  display: inline-block;
  margin-left: 2px;
  color: var(--color-primary);
  animation: cursor-blink 1s step-end infinite;
  font-weight: 600;
}
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
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
