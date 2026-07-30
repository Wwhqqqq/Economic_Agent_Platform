---
name: financial_audit
version: 1.2.0
apiVersion: skills.platform/v1

display:
  name: 财务审阅
  description: 基于三表数据输出结构化审阅意见与风险提示
  category: accounting
  category_label: 财会
  icon: audit
  tags: [财报, 审计, 三表]

invocation:
  slash_command: /financial_audit
  user_invocable: true
  expert_equippable: true

runtime:
  type: hybrid
  engine_preference: plan_execute
  pipeline: audit_flow
  fallback: react

requires:
  tools:
    - balance_sheet_analyzer
    - income_statement_analyzer
    - cash_flow_analyzer
    - financial_ratio_calculator
    - dupont_analysis
    - calculator

prompts:
  system: prompts/system.md

context:
  file: policies/context.yaml
---

# 财务审阅技能

端到端财务审计：分析资产负债表、利润表、现金流量表，计算关键比率，生成完整审计报告。
