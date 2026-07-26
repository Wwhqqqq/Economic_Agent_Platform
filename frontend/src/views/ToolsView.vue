<template>
  <div class="page-shell">
    <PageHeader
      title="工具能力库"
      subtitle="平台可调用的原子能力单元，按业务域分类管理，支持动态注册与编排调用。"
      breadcrumb="能力中心 / 工具能力库"
      :stats="[
        { label: '已注册工具', value: total, icon: Tools },
        { label: '能力域', value: categories.length, icon: Grid },
      ]"
    />

    <div class="page-body">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          placeholder="搜索工具名称或描述..."
          clearable
          class="search-input"
          :prefix-icon="Search"
        />
        <el-select v-model="filterCategory" placeholder="全部分类" clearable class="filter-select">
          <el-option v-for="c in categories" :key="c.key" :label="c.label" :value="c.key" />
        </el-select>
      </div>

      <div class="tools-grid">
        <GlassCard v-for="tool in filteredTools" :key="tool.name" hoverable class="tool-card">
          <div class="card-top">
            <el-tag size="small" effect="plain" type="primary">{{ tool.category_label }}</el-tag>
          </div>
          <h3>{{ tool.display_name }}</h3>
          <p>{{ tool.description }}</p>
          <div class="tags" v-if="tool.capability_tags?.length">
            <el-tag v-for="tag in tool.capability_tags" :key="tag" size="small" effect="plain" round>
              {{ tag }}
            </el-tag>
          </div>
        </GlassCard>
      </div>

      <EmptyState v-if="filteredTools.length === 0" title="未找到匹配的工具" description="试试调整搜索关键词或分类筛选">
        <template #icon>
          <el-icon :size="32" color="#94A3B8"><Search /></el-icon>
        </template>
      </EmptyState>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Tools, Grid } from '@element-plus/icons-vue'
import { fetchTools } from '../api/client'
import PageHeader from '../components/layout/PageHeader.vue'
import GlassCard from '../components/ui/GlassCard.vue'
import EmptyState from '../components/ui/EmptyState.vue'

const tools = ref<any[]>([])
const categories = ref<{ key: string; label: string }[]>([])
const total = ref(0)
const keyword = ref('')
const filterCategory = ref('')

const filteredTools = computed(() => {
  return tools.value.filter(t => {
    const matchCat = !filterCategory.value || t.category === filterCategory.value
    const kw = keyword.value.toLowerCase()
    const matchKw = !kw ||
      t.display_name?.toLowerCase().includes(kw) ||
      t.description?.toLowerCase().includes(kw) ||
      t.name?.toLowerCase().includes(kw)
    return matchCat && matchKw
  })
})

onMounted(async () => {
  try {
    const data = await fetchTools()
    tools.value = data.tools || []
    categories.value = data.categories || []
    total.value = data.total || tools.value.length
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-input {
  flex: 1;
  max-width: 400px;
}

.filter-select {
  width: 160px;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}

.tool-card h3 {
  font-size: 15px;
  font-weight: bold;
  margin: 10px 0 6px;
  color: var(--ui-text-primary);
}

.tool-card p {
  font-size: 13px;
  color: var(--ui-text-regular);
  line-height: 1.6;
  margin-bottom: 12px;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tool-id {
  font-size: 10px;
  color: var(--ui-text-secondary);
  background: var(--ui-bg-muted);
  padding: 2px 8px;
  border-radius: 4px;
}

.tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.default-icon {
  font-size: 28px;
}
</style>
