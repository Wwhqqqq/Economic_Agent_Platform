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
          <p class="panel-desc">将文本内容写入向量库与知识图谱，供智能体对话时检索增强。</p>
          <el-input
            v-model="uploadContent"
            type="textarea"
            :rows="6"
            placeholder="粘贴待入库的文档内容..."
            resize="vertical"
          />
          <button class="ui-btn-primary submit-btn" @click="uploadDoc">提交入库</button>
          <div class="file-row">
            <input type="file" accept=".txt,.md,.csv,.json" @change="onFileSelect" />
            <span class="file-hint">支持 .txt / .md / .csv / .json</span>
          </div>
          <div v-if="lastEntities.length" class="entities-block">
            <span class="entities-label">抽取实体</span>
            <el-tag v-for="e in lastEntities" :key="e.name" size="small" effect="plain" round>
              {{ e.name }} ({{ e.type }})
            </el-tag>
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
import { ref, onMounted } from 'vue'
import { Document, Link, Collection, Folder, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchKnowledgeStats, uploadKnowledge, uploadKnowledgeFile, fetchKnowledgeDocuments, deleteKnowledgeDocument, searchKnowledge } from '../api/client'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import EmptyState from '../components/ui/EmptyState.vue'

const stats = ref<any>({})
const documents = ref<any[]>([])
const lastEntities = ref<any[]>([])
const uploadContent = ref('')
const searchQuery = ref('')
const searchMode = ref('hybrid')
const searchResults = ref<any[]>([])
const searched = ref(false)

onMounted(async () => { await refreshAll() })

async function refreshAll() {
  try { stats.value = await fetchKnowledgeStats() } catch (e) { console.error(e) }
  try {
    const data = await fetchKnowledgeDocuments()
    documents.value = data.documents || []
    if (data.graph_available === false) stats.value.graph_available = false
  } catch (e) { console.error(e) }
}

async function uploadDoc() {
  if (!uploadContent.value.trim()) return
  try {
    const result = await uploadKnowledge(uploadContent.value)
    uploadContent.value = ''
    lastEntities.value = result.entities || []
    ElMessage.success(`文档已成功入库（抽取实体 ${result.entities_extracted || 0} 个）`)
    await refreshAll()
  } catch (e: any) {
    ElMessage.error('入库失败：' + e.message)
  }
}

async function onFileSelect(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const result = await uploadKnowledgeFile(file)
    lastEntities.value = result.entities || []
    ElMessage.success(`文件 ${file.name} 入库成功`)
    await refreshAll()
  } catch (err: any) {
    ElMessage.error('上传失败：' + err.message)
  }
}

async function removeDoc(docId: string) {
  try {
    await deleteKnowledgeDocument(docId)
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

.default-icon { font-size: 28px; }

.file-row { margin-top: 12px; display: flex; align-items: center; gap: 10px; }
.file-hint { font-size: 11px; color: var(--ui-text-secondary); }

.entities-block { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.entities-label { width: 100%; font-size: 12px; font-weight: 600; color: var(--ui-text-secondary); margin-bottom: 4px; }

.doc-list { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.doc-item {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 10px 12px; background: var(--ui-bg-muted); border-radius: 8px;
}
.doc-preview { font-size: 12px; color: var(--ui-text-regular); margin-left: 8px; }
.doc-index { font-size: 12px; font-weight: 600; color: var(--ui-text-primary); }
</style>
