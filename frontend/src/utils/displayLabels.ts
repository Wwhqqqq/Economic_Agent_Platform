/** 面向用户的产品化文案映射（发行版不暴露内部标识） */

const FALLBACK_TOOL_LABELS: Record<string, string> = {
  web_search: '信息检索',
  calculator: '数值计算',
  file_reader: '文档解析',
  code_executor: '数据计算',
  datetime: '时间查询',
  balance_sheet_analyzer: '资产负债表分析',
  income_statement_analyzer: '利润表分析',
  cash_flow_analyzer: '现金流量分析',
  financial_ratio_calculator: '财务比率分析',
  dupont_analysis: '杜邦分析',
}

const FALLBACK_SKILL_LABELS: Record<string, string> = {
  document_analysis: '文档洞察',
  data_visualization: '数据可视化',
  data_viz: '数据可视化',
  financial_audit: '财务审阅',
}

const FALLBACK_PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  openai: 'OpenAI',
  anthropic: 'Claude',
  custom: '本地模型',
}

let toolLabels = { ...FALLBACK_TOOL_LABELS }
let skillLabels = { ...FALLBACK_SKILL_LABELS }
let providerLabels = { ...FALLBACK_PROVIDER_LABELS }

export function setCatalogLabels(catalog: {
  tool_labels?: Record<string, string>
  skill_labels?: Record<string, string>
  provider_labels?: Record<string, string>
}) {
  if (catalog.tool_labels) toolLabels = { ...FALLBACK_TOOL_LABELS, ...catalog.tool_labels }
  if (catalog.skill_labels) skillLabels = { ...FALLBACK_SKILL_LABELS, ...catalog.skill_labels }
  if (catalog.provider_labels) providerLabels = { ...FALLBACK_PROVIDER_LABELS, ...catalog.provider_labels }
}

export function toolLabel(name: string) {
  return toolLabels[name] || '能力调用'
}

export function skillLabel(name: string) {
  return skillLabels[name] || '业务技能'
}

export function providerLabel(name: string) {
  return providerLabels[name] || name
}

export function stepLabel(title: string) {
  const t = title.toLowerCase()
  if (t.includes('plan') || t.includes('规划')) return '任务规划'
  if (t.includes('execute') || t.includes('执行')) return '步骤执行'
  if (t.includes('evaluate') || t.includes('评估')) return '结果评估'
  return title.replace(/_/g, ' ')
}
