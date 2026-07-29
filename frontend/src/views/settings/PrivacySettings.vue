<template>
  <div class="settings-panel">
    <SettingsBackBar />

    <GlassCard>
      <h3 class="panel-title">修改密码</h3>
      <p class="panel-desc">建议使用字母、数字、下划线组合的强密码。</p>

      <form class="password-form" @submit.prevent="handleSubmit">
        <div class="form-field" :class="{ 'field-error': errors.current_password }">
          <label>当前密码</label>
          <el-input
            v-model="form.currentPassword"
            type="password"
            show-password
            placeholder="请输入当前密码"
            @input="clearError('current_password')"
          />
          <p v-if="errors.current_password" class="error-text">{{ errors.current_password }}</p>
        </div>
        <div class="form-field" :class="{ 'field-error': errors.new_password }">
          <label>新密码</label>
          <el-input
            v-model="form.newPassword"
            type="password"
            show-password
            placeholder="至少 6 位，仅字母、数字、下划线"
            @input="clearError('new_password')"
          />
          <p v-if="errors.new_password" class="error-text">{{ errors.new_password }}</p>
        </div>
        <div class="form-field" :class="{ 'field-error': errors.confirm_password }">
          <label>确认新密码</label>
          <el-input
            v-model="form.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
            @input="clearError('confirm_password')"
          />
          <p v-if="errors.confirm_password" class="error-text">{{ errors.confirm_password }}</p>
        </div>
        <button type="submit" class="ui-btn-primary" :disabled="submitting">
          {{ submitting ? '保存中…' : '更新密码' }}
        </button>
      </form>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">登录与会话</h3>
      <dl class="info-list">
        <div class="info-row">
          <dt>最近登录</dt>
          <dd>{{ formatDateTime(auth.lastLoginAt) }}</dd>
        </div>
        <div class="info-row">
          <dt>当前会话</dt>
          <dd>您正在当前设备上使用</dd>
        </div>
        <div class="info-row">
          <dt>其他设备</dt>
          <dd class="muted">即将推出</dd>
        </div>
      </dl>
    </GlassCard>

    <GlassCard>
      <h3 class="panel-title">数据与权限</h3>
      <ul class="desc-list">
        <li><strong>对话数据</strong>：会话存储于服务端，仅本人可见。</li>
        <li><strong>知识库文档</strong>：上传文件归属当前账号；会员可访问专享知识库只读内容。</li>
        <li><strong>模型 API Key</strong>：会员个人 Key 加密存储，其他用户不可读取。</li>
      </ul>
      <div class="action-row">
        <button type="button" class="ui-btn-ghost" disabled>导出我的数据（即将推出）</button>
      </div>
      <p class="muted-link">需要注销账号？请联系管理员处理。</p>
    </GlassCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { changePassword } from '../../api/client'
import { validateConfirmPassword, validatePassword } from '../../utils/validation'
import GlassCard from '../../components/ui/GlassCard.vue'
import SettingsBackBar from '../../components/settings/SettingsBackBar.vue'

const auth = useAuthStore()
const submitting = ref(false)

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const errors = reactive<Record<string, string>>({
  current_password: '',
  new_password: '',
  confirm_password: '',
})

function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function clearError(field: string) {
  errors[field] = ''
}

function validateForm(): boolean {
  let ok = true
  if (!form.currentPassword) {
    errors.current_password = '请输入当前密码'
    ok = false
  }
  const pwdMsg = validatePassword(form.newPassword)
  if (pwdMsg) {
    errors.new_password = pwdMsg
    ok = false
  }
  const confirmMsg = validateConfirmPassword(form.newPassword, form.confirmPassword)
  if (confirmMsg) {
    errors.confirm_password = confirmMsg
    ok = false
  }
  return ok
}

async function handleSubmit() {
  if (!validateForm()) return
  submitting.value = true
  try {
    const data = await changePassword(form.currentPassword, form.newPassword)
    if (!data.success) {
      const field = data.field || 'current_password'
      errors[field] = data.message || '修改失败'
      return
    }
    form.currentPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
    await ElMessageBox.confirm('密码已更新，建议重新登录以确保安全。', '密码已更新', {
      confirmButtonText: '重新登录',
      cancelButtonText: '稍后',
      type: 'success',
    })
    auth.logout()
    window.location.href = '/login'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string; field?: string } } }
    const field = err.response?.data?.field || 'current_password'
    errors[field] = err.response?.data?.message || '修改失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  auth.refreshProfile()
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
}

.panel-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--ui-text-secondary);
}

.password-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--ui-text-regular);
}

.error-text {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ui-danger);
}

.info-list {
  margin: 0;
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
  text-align: right;
}

.info-row dd.muted {
  color: var(--ui-text-secondary);
}

.desc-list {
  margin: 0 0 16px;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ui-text-regular);
}

.action-row {
  margin-bottom: 10px;
}

.muted-link {
  margin: 0;
  font-size: 12px;
  color: var(--ui-text-secondary);
}
</style>
