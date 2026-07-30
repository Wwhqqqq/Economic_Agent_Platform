---
name: document_analysis
version: 1.1.0
apiVersion: skills.platform/v1

display:
  name: 文档洞察
  description: 深度文档分析：读取、摘要、提取关键信息并对比多个文档
  category: document
  category_label: 文档
  icon: document

invocation:
  slash_command: /document_analysis
  user_invocable: true
  expert_equippable: true

runtime:
  type: hybrid
  engine_preference: react
  fallback: react

requires:
  tools:
    - file_reader
    - calculator
    - code_executor
    - web_search

prompts:
  system: prompts/system.md

context:
  file: policies/context.yaml
---

# 文档分析技能

读取、摘要、提取关键信息并对比多个文档。
