<template>
  <div class="settings-panel">
    <SettingsBackBar />

    <GlassCard class="profile-card">
      <h3 class="panel-title">头像</h3>
      <p class="panel-desc">支持 JPG、PNG 格式，大小不超过 2MB。</p>
      <div class="avatar-section">
        <div class="avatar-preview" :class="{ member: auth.isMember }">
          <img v-if="auth.avatarUrl" :src="auth.avatarUrl" alt="头像" class="avatar-img" />
          <span v-else>{{ userInitial }}</span>
        </div>
        <div class="avatar-actions">
          <label class="ui-btn-ghost avatar-upload-btn">
            上传头像
            <input type="file" accept="image/*" hidden @change="onAvatarChange" />
          </label>
          <button
            v-if="auth.avatarUrl"
            type="button"
            class="ui-btn-ghost"
            @click="removeAvatar"
          >
            恢复默认
          </button>
        </div>
      </div>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">修改用户名</h3>
      <form class="edit-form" @submit.prevent="saveUsername">
        <el-input v-model="usernameForm" placeholder="字母、数字、下划线，3–64 位" />
        <p v-if="usernameError" class="error-text">{{ usernameError }}</p>
        <button type="submit" class="ui-btn-primary" :disabled="savingUsername">
          {{ savingUsername ? '保存中…' : '保存用户名' }}
        </button>
      </form>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">绑定邮箱</h3>
      <p class="panel-desc">当前邮箱：{{ auth.email || '未绑定' }}</p>
      <form class="edit-form" @submit.prevent="saveEmail">
        <el-input v-model="emailForm" placeholder="请输入新邮箱地址" />
        <div class="code-row">
          <el-input
            v-model="emailCode"
            placeholder="4 位验证码"
            maxlength="4"
          />
          <button
            type="button"
            class="ui-btn-ghost send-code-btn"
            :disabled="sendingCode || emailCooldown > 0"
            @click="sendEmailCode"
          >
            {{ emailCooldown > 0 ? `${emailCooldown}s 后重发` : sendingCode ? '发送中…' : '发送验证码' }}
          </button>
        </div>
        <p v-if="emailError" class="error-text">{{ emailError }}</p>
        <button type="submit" class="ui-btn-primary" :disabled="savingEmail">
          {{ savingEmail ? '绑定中…' : '绑定邮箱' }}
        </button>
      </form>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">账号信息</h3>
      <dl class="info-list">
        <div class="info-row">
          <dt>用户 ID</dt>
          <dd class="muted">
            {{ auth.userId ?? '—' }}
            <button v-if="auth.userId" type="button" class="copy-btn" @click="copyUserId">复制</button>
          </dd>
        </div>
        <div class="info-row">
          <dt>账号类型</dt>
          <dd class="badge-row">
            <MembershipBadge
              :is-member="auth.isMember"
              :membership-expires-at="auth.membershipExpiresAt"
              size="sm"
              :show-expiry="auth.isMember"
            />
          </dd>
        </div>
        <div class="info-row">
          <dt>注册时间</dt>
          <dd>{{ formatDateTime(auth.createdAt) }}</dd>
        </div>
      </dl>
    </GlassCard>

    <GlassCard class="membership-card">
      <h3 class="panel-title">会员摘要</h3>
      <p v-if="auth.isMember" class="panel-desc">
        您的会员有效期至 {{ formatDateTime(auth.membershipExpiresAt) }}
        <span v-if="daysRemaining !== null">（剩余 {{ daysRemaining }} 天）</span>
      </p>
      <p v-else class="panel-desc">
        升级会员后可使用 Plan-Execute、Multi-Agent、个人模型配置等高级能力。
      </p>
      <div class="action-row">
        <router-link to="/membership" class="ui-btn-primary link-btn">
          {{ auth.isMember ? '管理会员' : '升级会员' }}
        </router-link>
      </div>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">账号操作</h3>
      <div class="action-row">
        <button type="button" class="ui-btn-ghost" @click="confirmSwitchAccount">
          切换账号
        </button>
      </div>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { useAuthActions } from '../../composables/useAuthActions'
import { sendBindEmailCode } from '../../api/client'
import { validateEmail, validateUsername } from '../../utils/validation'
import { readImageFileAsAvatar } from '../../utils/avatar'
import GlassCard from '../../components/ui/GlassCard.vue'
import MembershipBadge from '../../components/ui/MembershipBadge.vue'
import SettingsBackBar from '../../components/settings/SettingsBackBar.vue'

const auth = useAuthStore()
const { confirmSwitchAccount } = useAuthActions()

const usernameForm = ref('')
const emailForm = ref('')
const emailCode = ref('')
const usernameError = ref('')
const emailError = ref('')
const savingUsername = ref(false)
const savingEmail = ref(false)
const sendingCode = ref(false)
const emailCooldown = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const userInitial = computed(() => {
  const name = auth.username
  return name ? name.charAt(0).toUpperCase() : '?'
})

const daysRemaining = computed(() => {
  if (!auth.membershipExpiresAt) return null
  const end = new Date(auth.membershipExpiresAt).getTime()
  const diff = Math.ceil((end - Date.now()) / (1000 * 60 * 60 * 24))
  return diff > 0 ? diff : 0
})

function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function startCooldown(seconds: number) {
  emailCooldown.value = seconds
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    if (emailCooldown.value <= 1) {
      emailCooldown.value = 0
      if (cooldownTimer) clearInterval(cooldownTimer)
      cooldownTimer = null
    } else {
      emailCooldown.value -= 1
    }
  }, 1000)
}

async function onAvatarChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const dataUrl = await readImageFileAsAvatar(file)
    auth.setAvatarUrl(dataUrl)
    ElMessage.success('头像已更新')
  } catch (err: unknown) {
    ElMessage.error(err instanceof Error ? err.message : '上传失败')
  } finally {
    input.value = ''
  }
}

function removeAvatar() {
  auth.setAvatarUrl(null)
  ElMessage.success('已恢复默认头像')
}

async function saveUsername() {
  usernameError.value = ''
  const msg = validateUsername(usernameForm.value)
  if (msg) {
    usernameError.value = msg
    return
  }
  if (usernameForm.value.trim() === auth.username) {
    ElMessage.info('用户名未变更')
    return
  }
  savingUsername.value = true
  try {
    await auth.updateProfile({ username: usernameForm.value.trim() })
    ElMessage.success('用户名已更新')
  } catch (e: unknown) {
    const err = e as Error & { field?: string }
    usernameError.value = err.message || '更新失败'
  } finally {
    savingUsername.value = false
  }
}

async function sendEmailCode() {
  emailError.value = ''
  const msg = validateEmail(emailForm.value)
  if (msg) {
    emailError.value = msg
    return
  }
  sendingCode.value = true
  try {
    const data = await sendBindEmailCode(emailForm.value.trim())
    if (!data.success) {
      emailError.value = data.message || '发送失败'
      if (data.retry_after_seconds) startCooldown(data.retry_after_seconds)
      return
    }
    ElMessage.success('验证码已发送（开发环境请查看后端控制台）')
    startCooldown(data.retry_after_seconds ?? 60)
  } catch (e: unknown) {
    emailError.value = e instanceof Error ? e.message : '发送失败'
  } finally {
    sendingCode.value = false
  }
}

async function saveEmail() {
  emailError.value = ''
  const emailMsg = validateEmail(emailForm.value)
  if (emailMsg) {
    emailError.value = emailMsg
    return
  }
  if (!emailCode.value.trim()) {
    emailError.value = '请输入验证码'
    return
  }
  savingEmail.value = true
  try {
    await auth.updateProfile({
      email: emailForm.value.trim(),
      verification_code: emailCode.value.trim(),
    })
    ElMessage.success('邮箱绑定成功')
    emailCode.value = ''
  } catch (e: unknown) {
    const err = e as Error & { field?: string }
    emailError.value = err.message || '绑定失败'
  } finally {
    savingEmail.value = false
  }
}

async function copyUserId() {
  if (!auth.userId) return
  try {
    await navigator.clipboard.writeText(String(auth.userId))
    ElMessage.success('用户 ID 已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

onMounted(async () => {
  await auth.refreshProfile()
  usernameForm.value = auth.username
  emailForm.value = auth.email || ''
})

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
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
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--ui-text-secondary);
  line-height: 1.5;
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-preview {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  background: var(--gradient-primary);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-preview.member {
  background: linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.avatar-upload-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.code-row {
  display: flex;
  gap: 10px;
}

.send-code-btn {
  flex-shrink: 0;
  white-space: nowrap;
}

.error-text {
  margin: 0;
  font-size: 12px;
  color: var(--ui-danger);
}

.info-list {
  margin: 0;
}

.info-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--settings-list-divider, rgba(199, 210, 254, 0.35));
}

.info-row:last-child {
  border-bottom: none;
}

.info-row dt {
  font-size: 13px;
  font-weight: 600;
  color: var(--ui-text-regular);
  flex-shrink: 0;
  width: 80px;
}

.info-row dd {
  margin: 0;
  font-size: 13px;
  color: var(--ui-text-primary);
  text-align: right;
  word-break: break-all;
}

.info-row dd.muted {
  color: var(--ui-text-secondary);
}

.badge-row {
  display: flex;
  justify-content: flex-end;
}

.copy-btn {
  margin-left: 8px;
  border: none;
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}
</style>
