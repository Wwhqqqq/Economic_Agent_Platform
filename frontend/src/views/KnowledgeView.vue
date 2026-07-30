<template>

  <div class="page-shell">

    <PageHeader

      title="知识资产"

      subtitle="统一管理企业文档与结构化知识，支持向量语义检索与知识图谱关联查询的混合检索策略。"

      breadcrumb="能力中心 / 知识资产"

      :stats="[

        { label: '向量文档', value: stats.vector_docs || 0, icon: Document },

        { label: '图谱实体', value: stats.graph_entities || 0, icon: Link },

        { label: '图谱文档', value: stats.graph_documents || 0, icon: Collection },

      ]"

    />



    <div class="page-body">

      <div class="content-grid">

        <GlassCard class="panel">

          <h3 class="section-title panel-title">文档入库</h3>

          <p class="panel-desc">支持文本、PDF（可复制文本层）与图片 OCR 入库。上传后后台自动分块解析。</p>

          <el-input

            v-model="uploadContent"

            type="textarea"

            :rows="6"

            placeholder="粘贴待入库的文档内容..."

            resize="vertical"

          />

          <button class="ui-btn-primary submit-btn" :disabled="uploading" @click="uploadDoc">

            {{ uploading ? '提交中...' : '提交入库' }}

          </button>

          <div class="file-row">

            <input
              type="file"
              accept=".txt,.md,.csv,.json,.pdf,.png,.jpg,.jpeg,.webp"
              :disabled="uploading"
              @change="onFileSelect"
            />
            <span class="file-hint">支持 .txt / .md / .csv / .json / .pdf / .png / .jpg / .webp</span>
          </div>
          <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress">
            <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
            <span class="progress-label">上传中 {{ uploadProgress }}%</span>
          </div>

          <div v-if="parsingDocs.length" class="parsing-block">

            <span class="entities-label">解析中</span>

            <div v-for="p in parsingDocs" :key="p.doc_id" class="parsing-item">

              <span>{{ p.title }}</span>

              <el-tag size="small" type="warning">{{ parseStatusLabel(p.parse_status) }}</el-tag>

            </div>

          </div>

        </GlassCard>



        <GlassCard class="panel">

          <h3 class="section-title panel-title">文档列表</h3>

          <p class="panel-desc">仅展示当前账号上传的私有文档。</p>

          <el-alert v-if="stats.graph_available === false" type="warning" show-icon :closable="false" title="知识图谱服务暂不可用，入库仍可写入向量库" />

          <div v-if="documents.length" class="doc-list">

            <div v-for="(d, idx) in documents" :key="d.doc_id" class="doc-item">

              <div>

                <span class="doc-index">{{ d.title || `文档 ${idx + 1}` }}</span>

                <el-tag size="small" :type="parseTagType(d.parse_status)" effect="plain" round>

                  {{ parseStatusLabel(d.parse_status) }}

                </el-tag>

                <span v-if="d.source_type && d.source_type !== 'text'" class="doc-meta">{{ sourceTypeLabel(d.source_type) }}</span>
                <span v-if="d.doc_class" class="doc-meta">{{ docClassLabel(d.doc_class) }}</span>
                <span v-if="d.table_count" class="doc-meta">{{ d.table_count }} 表</span>
                <span v-if="d.quality_score != null && d.quality_score < 0.75" class="doc-meta doc-meta-warn">低质量</span>
                <span v-if="d.page_count" class="doc-meta">{{ d.page_count }} 页</span>
                <span v-if="d.chunk_count" class="doc-meta">{{ d.chunk_count }} 块</span>

                <span class="doc-preview">{{ d.preview }}</span>

              </div>

              <button class="ui-btn-ghost" @click="removeDoc(d.doc_id)">删除</button>

            </div>

          </div>

          <EmptyState v-else title="暂无文档" description="上传文本或文件开始构建知识库">

            <template #icon><el-icon :size="32" color="#94A3B8"><Folder /></el-icon></template>

          </EmptyState>

        </GlassCard>



        <GlassCard class="panel">

          <h3 class="section-title panel-title">知识检索</h3>

          <p class="panel-desc">支持混合检索（向量 + 图谱 RRF 融合）、纯向量检索、纯图谱检索三种模式。</p>

          <div class="search-row">

            <el-input

              v-model="searchQuery"

              placeholder="输入检索关键词..."

              clearable

              @keydown.enter="search"

            />

            <el-select v-model="searchMode" class="mode-select">

              <el-option label="混合检索" value="hybrid" />

              <el-option label="向量语义检索" value="vector" />

              <el-option label="知识图谱检索" value="graph" />

            </el-select>

            <button class="ui-btn-primary" @click="search">执行检索</button>

          </div>



          <div v-if="searchResults.length > 0" class="search-results">

            <GlassCard v-for="(r, i) in searchResults" :key="i" class="search-item">

              <div class="result-meta">

                <el-icon><Document /></el-icon>

                来源：{{ r.metadata?.source || '未知' }}

                <span v-if="r.metadata?.section_path && !r.metadata?.page_range"> · 章节：{{ r.metadata.section_path }}</span>
                <span v-if="r.metadata?.page_range && r.metadata?.section_path"> · {{ r.metadata.section_path }}</span>

                · 相关度：{{ formatScore(r.metadata) }}

              </div>

              <pre>{{ r.content }}</pre>

            </GlassCard>

          </div>

          <EmptyState

            v-else-if="searched"

            title="未检索到相关内容"

            description="尝试更换关键词或切换检索模式"

          >

            <template #icon><el-icon :size="32" color="#94A3B8"><Search /></el-icon></template>

          </EmptyState>

        </GlassCard>

      </div>

    </div>

  </div>

</template>



<script setup lang="ts">

import { ref, onMounted, onUnmounted } from 'vue'

import { Document, Link, Collection, Folder, Search } from '@element-plus/icons-vue'

import { ElMessage } from 'element-plus'

import {

  fetchKnowledgeStats,

  uploadKnowledge,

  uploadKnowledgeFile,

  fetchKnowledgeDocuments,

  fetchKnowledgeDocStatus,

  deleteKnowledgeDocument,

  searchKnowledge,

} from '../api/client'

import PageHeader from '../components/layout/PageHeader.vue'

import GlassCard from '../components/ui/GlassCard.vue'

import EmptyState from '../components/ui/EmptyState.vue'



const stats = ref<any>({})

const documents = ref<any[]>([])

const parsingDocs = ref<any[]>([])

const uploadContent = ref('')

const uploading = ref(false)
const uploadProgress = ref(0)

const searchQuery = ref('')

const searchMode = ref('hybrid')

const searchResults = ref<any[]>([])

const searched = ref(false)



let pollTimer: ReturnType<typeof setInterval> | null = null



onMounted(async () => {

  await refreshAll()

  startPolling()

})



onUnmounted(() => {

  if (pollTimer) clearInterval(pollTimer)

})



function parseStatusLabel(status?: string) {

  const map: Record<string, string> = {

    pending: '等待中',

    parsing: '解析中',

    ready: '就绪',

    failed: '失败',

    needs_review: '待审核',

  }

  return map[status || 'ready'] || status || '就绪'

}



function parseTagType(status?: string) {

  if (status === 'ready') return 'success'

  if (status === 'parsing' || status === 'pending') return 'warning'

  if (status === 'failed') return 'danger'

  if (status === 'needs_review') return 'info'

  return 'info'

}



function docClassLabel(cls?: string) {
  const map: Record<string, string> = {
    native_text: '文本 PDF',
    table_heavy: '表格密集',
    financial_report: '财报',
    scanned: '扫描件',
    scanned_ocr: '扫描 OCR',
  }
  return map[cls || ''] || cls || ''
}

function sourceTypeLabel(type?: string) {
  const map: Record<string, string> = {
    pdf: 'PDF',
    image: '图片',
    text: '文本',
  }
  return map[type || 'text'] || type || ''
}



function startPolling() {

  if (pollTimer) clearInterval(pollTimer)

  pollTimer = setInterval(async () => {

    if (!parsingDocs.value.length) return

    await pollParsingDocs()

  }, 2000)

}



async function pollParsingDocs() {

  const pending = parsingDocs.value.filter(

    (d) => d.parse_status === 'parsing' || d.parse_status === 'pending'

  )

  if (!pending.length) {

    parsingDocs.value = []

    return

  }

  let changed = false

  for (const doc of pending) {

    try {

      const status = await fetchKnowledgeDocStatus(doc.doc_id)

      doc.parse_status = status.parse_status

      doc.chunk_count = status.chunk_count

      if (status.parse_status === 'ready') {

        ElMessage.success(`《${doc.title}》解析完成，共 ${status.chunk_count} 个分块`)

        changed = true

      } else if (status.parse_status === 'needs_review') {
        ElMessage.warning(`《${doc.title}》需人工审核：${status.error_message || '扫描件或 OCR 质量不足'}`)
        changed = true
      } else if (status.parse_status === 'failed') {

        ElMessage.error(`《${doc.title}》解析失败：${status.error_message || '未知错误'}`)

        changed = true

      }

    } catch (e) {

      console.error(e)

    }

  }

  parsingDocs.value = parsingDocs.value.filter(

    (d) => d.parse_status === 'parsing' || d.parse_status === 'pending'

  )

  if (changed) await refreshAll()

}



async function refreshAll() {

  try { stats.value = await fetchKnowledgeStats() } catch (e) { console.error(e) }

  try {

    const data = await fetchKnowledgeDocuments()

    documents.value = data.documents || []

    if (data.graph_available === false) stats.value.graph_available = false

  } catch (e) { console.error(e) }

}



async function uploadDoc() {

  if (!uploadContent.value.trim() || uploading.value) return

  uploading.value = true

  try {

    const result = await uploadKnowledge(uploadContent.value)

    uploadContent.value = ''

    parsingDocs.value.push({

      doc_id: result.doc_id,

      title: result.title,

      parse_status: result.parse_status || result.status || 'parsing',

    })

    ElMessage.success('已提交入库，后台正在分块解析…')

    startPolling()

    await refreshAll()

  } catch (e: any) {

    ElMessage.error('入库失败：' + e.message)

  } finally {

    uploading.value = false

  }

}



async function onFileSelect(e: Event) {

  const file = (e.target as HTMLInputElement).files?.[0]

  if (!file || uploading.value) return

  uploading.value = true

  uploadProgress.value = 15

  try {

    uploadProgress.value = 45

    const ext = file.name.split('.').pop()?.toLowerCase() || ''

    const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'].includes(ext)

    const { uploadKnowledgeMedia } = await import('../api/client')

    const result = isImage ? await uploadKnowledgeMedia(file) : await uploadKnowledgeFile(file)

    uploadProgress.value = 100

    parsingDocs.value.push({

      doc_id: result.doc_id,

      title: result.title || file.name,

      parse_status: result.parse_status || result.status || 'parsing',

    })

    ElMessage.success(`文件 ${file.name} 已提交，后台解析中…`)

    startPolling()

    await refreshAll()

  } catch (err: any) {

    ElMessage.error('上传失败：' + err.message)

  } finally {

    uploading.value = false

    setTimeout(() => { uploadProgress.value = 0 }, 800)

    ;(e.target as HTMLInputElement).value = ''

  }

}



async function removeDoc(docId: string) {

  try {

    await deleteKnowledgeDocument(docId)

    parsingDocs.value = parsingDocs.value.filter((d) => d.doc_id !== docId)

    ElMessage.success('已删除')

    await refreshAll()

  } catch (e: any) {

    ElMessage.error(e.message)

  }

}



function formatScore(metadata: any) {

  const score = metadata?.rrf_score ?? metadata?.score ?? 0

  return Number(score).toFixed(3)

}



async function search() {

  if (!searchQuery.value.trim()) return

  searched.value = true

  try {

    const data = await searchKnowledge(searchQuery.value, 5, searchMode.value)

    searchResults.value = data.results || []

  } catch (e: any) {

    ElMessage.error('检索失败：' + e.message)

  }

}

</script>



<style scoped>

.content-grid {

  display: flex;

  flex-direction: column;

  gap: 16px;

}



.panel-title {

  font-size: 15px;

  margin-bottom: 8px;

}



.panel-desc {

  font-size: 13px;

  color: var(--ui-text-regular);

  margin-bottom: 14px;

  padding-left: 14px;

}



.submit-btn {

  margin-top: 12px;

}



.search-row {

  display: flex;

  gap: 10px;

  flex-wrap: wrap;

}



.search-row .el-input {

  flex: 1;

  min-width: 200px;

}



.mode-select {

  width: 160px;

}



.search-results {

  margin-top: 16px;

  display: flex;

  flex-direction: column;

  gap: 10px;

}



.search-item {

  padding: 14px 18px !important;

}



.result-meta {

  display: flex;

  align-items: center;

  gap: 6px;

  font-size: 12px;

  color: var(--ui-primary);

  font-weight: 600;

  margin-bottom: 8px;

}



.search-item pre {

  font-size: 13px;

  color: var(--ui-text-regular);

  white-space: pre-wrap;

  font-family: var(--ui-font);

  line-height: 1.6;

}



.file-row { margin-top: 12px; display: flex; align-items: center; gap: 10px; }

.file-hint { font-size: 11px; color: var(--ui-text-secondary); }



.parsing-block { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; }

.parsing-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }

.entities-label { font-size: 12px; font-weight: 600; color: var(--ui-text-secondary); }



.doc-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }

.doc-item {

  display: flex; justify-content: space-between; align-items: center; gap: 12px;

  padding: 10px 12px; background: var(--ui-bg-muted); border-radius: 8px;

}

.doc-preview { font-size: 12px; color: var(--ui-text-regular); margin-left: 8px; display: block; margin-top: 4px; }

.doc-index { font-size: 12px; font-weight: 600; color: var(--ui-text-primary); margin-right: 8px; }

.doc-meta { font-size: 11px; color: var(--ui-text-secondary); margin-left: 8px; }

.doc-meta-warn { color: #d97706; font-weight: 600; }
.upload-progress { margin-top: 10px; background: var(--ui-bg-muted); border-radius: 8px; height: 8px; position: relative; overflow: hidden; }
.progress-bar { height: 100%; background: linear-gradient(90deg, #4F46E5, #6366F1); transition: width 0.2s; }
.progress-label { font-size: 11px; color: var(--ui-text-secondary); display: block; margin-top: 4px; }

</style>

