---
name: data_visualization
version: 1.0.0
apiVersion: skills.platform/v1

display:
  name: 数据可视化
  description: 基于结构化数据生成数据可视化图表
  category: data
  category_label: 数据
  icon: chart

invocation:
  slash_command: /data_visualization
  user_invocable: true
  expert_equippable: true

runtime:
  type: hybrid
  engine_preference: react
  fallback: react

requires:
  tools:
    - file_reader
    - code_executor
    - calculator

prompts:
  system: prompts/system.md

context:
  file: policies/context.yaml
---

# 数据可视化技能

通过代码执行生成图表，辅助数据分析。
