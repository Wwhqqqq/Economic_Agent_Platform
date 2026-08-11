<template>
  <div
    class="attachment-upload"
    :class="{ dragging: isDragging }"
    @dragover.prevent="isDragging = true"
    @dragleave.prevent="isDragging = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="fileInputRef"
      type="file"
      :accept="acceptTypes"
      multiple
      class="hidden-input"
      @change="onFileChange"
    />
    <div v-if="items.length" class="preview-row">
      <div
        v-for="(item, i) in items"
        :key="item.asset_id || item.preview_url || item.filename + i"
        class="preview-item"
        :class="{ 'is-file': item.kind === 'file' }"
      >
        <img v-if="item.kind !== 'file' && item.preview_url" :src="item.preview_url" :alt="item.filename" />
        <div v-else class="file-chip">
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ item.filename }}</span>
        </div>
        <button type="button" class="remove-btn" @click="remove(i)">×</button>
        <span v-if="item.uploading" class="upload-tag">上传中</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { uploadChatAttachment, type ChatAttachmentMeta } from '../../api/media'

export interface AttachmentItem extends ChatAttachmentMeta {
  preview_url?: string
  uploading?: boolean
}

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'])
const FILE_EXTS = new Set(['txt', 'md', 'csv', 'json', 'pdf', 'xlsx', 'xls', 'doc', 'docx', 'log'])

const acceptTypes = [
  'image/png,image/jpeg,image/webp,image/gif,image/bmp',
  '.txt,.md,.csv,.json,.pdf,.xlsx,.xls,.doc,.docx,.log',
].join(',')

const props = defineProps<{
  disabled?: boolean
  maxCount?: number
}>()

const emit = defineEmits<{
  update: [items: AttachmentItem[]]
}>()

const items = ref<AttachmentItem[]>([])
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement>()

const maxCount = props.maxCount ?? 4

function fileExtension(name: string): string {
  const parts = name.split('.')
  return parts.length > 1 ? parts.pop()!.toLowerCase() : ''
}

function isAllowedFile(file: File): boolean {
  const ext = fileExtension(file.name)
  if (IMAGE_EXTS.has(ext) || FILE_EXTS.has(ext)) return true
  if (file.type.startsWith('image/')) return true
  return false
}

function isImageFile(file: File): boolean {
  const ext = fileExtension(file.name)
  if (IMAGE_EXTS.has(ext)) return true
  return file.type.startsWith('image/')
}

function emitUpdate() {
  emit('update', [...items.value])
}

const hasUploading = () => items.value.some(i => i.uploading)

async function addFiles(files: FileList | File[]) {
  const list = Array.from(files).filter(isAllowedFile)
  if (!list.length) {
    ElMessage.warning('不支持的文件类型')
    return
  }
  for (const file of list) {
    if (items.value.length >= maxCount) {
      ElMessage.warning(`最多上传 ${maxCount} 个附件`)
      break
    }
    const isImage = isImageFile(file)
    const preview_url = isImage ? URL.createObjectURL(file) : undefined
    const pending: AttachmentItem = {
      asset_id: '',
      filename: file.name,
      mime_type: file.type || 'application/octet-stream',
      kind: isImage ? 'image' : 'file',
      preview_url,
      uploading: true,
    }
    items.value.push(pending)
    emitUpdate()
    try {
      const meta = await uploadChatAttachment(file)
      Object.assign(pending, meta, {
        preview_url: isImage ? preview_url : undefined,
        uploading: false,
        kind: meta.kind || (isImage ? 'image' : 'file'),
      })
      ElMessage.success(`${file.name} 上传成功`)
    } catch (e) {
      items.value = items.value.filter(i => i !== pending)
      if (preview_url?.startsWith('blob:')) URL.revokeObjectURL(preview_url)
      ElMessage.error(e instanceof Error ? e.message : '上传失败')
    }
  }
  emitUpdate()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) addFiles(input.files)
  input.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (props.disabled) return
  if (e.dataTransfer?.files?.length) addFiles(e.dataTransfer.files)
}

function remove(index: number) {
  const item = items.value[index]
  if (item?.preview_url?.startsWith('blob:')) URL.revokeObjectURL(item.preview_url)
  items.value.splice(index, 1)
  emitUpdate()
}

function clear() {
  for (const item of items.value) {
    if (item.preview_url?.startsWith('blob:')) URL.revokeObjectURL(item.preview_url)
  }
  items.value = []
  emitUpdate()
}

function openPicker() {
  if (props.disabled) return
  fileInputRef.value?.click()
}

defineExpose({ clear, items, openPicker, addFiles, hasUploading })
</script>

<style scoped>
.attachment-upload {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.attachment-upload.dragging {
  outline: 2px dashed rgba(99, 102, 241, 0.45);
  border-radius: 10px;
  padding: 4px;
}
.hidden-input { display: none; }
.preview-row { display: flex; flex-wrap: wrap; gap: 8px; width: 100%; }
.preview-item {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(199, 210, 254, 0.5);
  background: rgba(255, 255, 255, 0.9);
}
.preview-item.is-file {
  width: auto;
  min-width: 120px;
  max-width: 200px;
  height: 40px;
  padding: 0 28px 0 8px;
}
.preview-item img { width: 100%; height: 100%; object-fit: cover; }
.file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 100%;
  font-size: 12px;
  color: var(--ui-text-secondary);
}
.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}
.remove-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
}
.upload-tag {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  font-size: 10px;
  text-align: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
}
</style>
