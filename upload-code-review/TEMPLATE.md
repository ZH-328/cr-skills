# 代码审查报告 JSON 规范

上传到Aegis平台的代码审查结果需符合指定 JSON 格式，必须严格遵循示例规范。

## 重要说明

必须包含以下两个部分：
1. `review_record`：包含整体审查评分的对象
2. `findings`：包含具体代码问题列表的数组

### 关于 matched_rule_ids 字段

**必须严格遵守以下规则**：
- 只有当问题真正匹配到具体的预定义代码审查规则时，才在 `matched_rule_ids` 中填写对应的规则ID
- 如果是通过代码分析自动检测发现的问题，但没有对应的预定义规则，**必须将 `matched_rule_ids` 设置为空数组 `[]`**
- **严禁**为自动检测的问题自动分配递增的数字ID或随意填写规则ID

### 正确示例
```json
// 匹配到具体规则的情况
"matched_rule_ids": [1, 2]

// 自动检测但无对应规则的情况
"matched_rule_ids": []
```

上传json文件格式规范：
```json
{
  "review_record": {
    "score": 0-100
  },
  "findings": [
    {
      "title": "问题概述",
      "file": "src/path/to/file.py",
      "line_number_pairs": [{"start": 10, "end": 20}],
      "summary": "一句话总结该问题",
      "message": "详细描述为何是问题，并指出根因",
      "suggestion": "修复建议/示例方案",
      "severity": "严重|高|中|低",
      "category": "bug|建议|提示",
      "matched_rule_ids": [1,2]
    }
  ]
}