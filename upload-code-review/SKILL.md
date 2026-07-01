---
name: upload-code-review
description: Upload code review data to the Aegis platform for centralized tracking and management.
metadata:
  short-description: Upload Aegis code review JSON
---

# 上传代码审查到平台技能

## 说明

1. 按照[模板json](TEMPLATE.md)生成JSON格式的代码审查数据，语言为中文，json文件命名应该为`code-review-<月日时分>.json`，生成的json文件存储在`.tmp/code-review`目录下。
2. 必须完全遵循[TEMPLATE.md](TEMPLATE.md)中的JSON规范。
3. 运行上传脚本，将代码审查数据提交到Aegis平台。
4. 上传成功后，脚本会根据 `--file-path` 定位被审查仓库，并删除该仓库下的 `.tmp` 目录和 `CHANGELOG.md`。
5. 请勿修改命令或添加其他标志。

## 上传过程

> 脚本路径相对于该skill目录。执行脚本时请从`upload-code-review` skill目录开始执行，或保持等价的相对路径。

````bash
python scripts/uploader.py --file-path <代码审查数据JSON文件路径>
````

### 填写参数
- `--file-path`：包含要上传的代码审查数据的 JSON 文件的路径。

### 最佳实践

````bash
python scripts/uploader.py --file-path ".tmp/code-review/code-review-123.json"
````
