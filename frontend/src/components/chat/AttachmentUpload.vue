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
      accept="image/png,image/jpeg,image/webp,image/gif,image/bmp"
      multiple
      class="hidden-input"
      @change="onFileChange"
    />
    <button type="button" class="attach-btn" :disabled="disabled" @click="fileInputRef?.click()">
      <el-icon><Picture /></el-icon>
      图片
    </button>
    <div v-if="items.length" class="preview-row">
      <div v-for="(item, i) in items" :key="item.asset_id || item.preview_url" class="preview-item">
        <img :src="item.preview_url" :alt="item.filename" />
        <button type="button" class="remove-btn" @click="remove(i)">×</button>
        <span v-if="item.uploading" class="upload-tag">上传中</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Picture } from '@element-plus/icons-vue'
import { uploadChatAttachment, type ChatAttachmentMeta } from '../../api/media'

export interface AttachmentItem extends ChatAttachmentMeta {
  preview_url: string
  uploading?: boolean
}

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

function emitUpdate() {
  emit('update', items.value.filter(i => !i.uploading && i.asset_id))
}

async function addFiles(files: FileList | File[]) {
  const list = Array.from(files).filter(f => f.type.startsWith('image/'))
  for (const file of list) {
    if (items.value.length >= maxCount) break
    const preview_url = URL.createObjectURL(file)
    const pending: AttachmentItem = {
      asset_id: '',
      filename: file.name,
      mime_type: file.type,
      preview_url,
      uploading: true,
    }
    items.value.push(pending)
    try {
      const meta = await uploadChatAttachment(file)
      Object.assign(pending, meta, { preview_url, uploading: false })
    } catch (e) {
      items.value = items.value.filter(i => i !== pending)
      URL.revokeObjectURL(preview_url)
      console.error(e)
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

defineExpose({ clear, items })
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
.attach-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(199, 210, 254, 0.6);
  background: rgba(255, 255, 255, 0.85);
  color: var(--color-primary);
  font-size: 12px;
  cursor: pointer;
}
.attach-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.preview-row { display: flex; flex-wrap: wrap; gap: 8px; }
.preview-item {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(199, 210, 254, 0.5);
}
.preview-item img { width: 100%; height: 100%; object-fit: cover; }
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
