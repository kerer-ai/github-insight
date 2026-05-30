---
name: github-community-insight
description: 监测 GitHub 开源社区的 issue 动态，从近期 issue 中识别 RFC/设计提案/重大方案，及时洞察社区技术规划和演进方向，生成结构化 MD 报告。当用户关注社区动向、需要了解某个仓库的近期技术讨论、想知道项目路线图或架构变更时触发。
---

# GitHub 社区洞察

监测 GitHub 开源社区的 issue 动态，使用 AI 识别 RFC/设计提案/重大方案类 issue，
输出标准化 Markdown 报告到当前项目的 `docs/` 目录。

## 架构

两个核心能力均由大模型驱动：

1. **Issue 分类** — LLM 逐条阅读 issue 标题和描述，基于语义判断是否属于架构演进/重大方案
2. **核心洞察** — LLM 综合分类结果，撰写本期社区关注重点的叙述性总结

脚本负责机械性工作：`gh` CLI 调用、JSON 数据处理、Markdown 格式化。

## 输入参数

- **target**：GitHub 仓库名（`owner/repo`），支持逗号分隔多个目标
- **days**：回溯天数（默认 7 天）

如果用户未提供 target，使用 `AskUserQuestion` 交互式询问。

## 工作流

按顺序执行。所有命令在终端中运行，工作目录为当前项目根目录。

### 步骤 1：获取 Issues

```bash
python3 ~/.claude/skills/github-community-insight/scripts/fetch_issues.py \
  --repo <owner/repo> --days <N> -o ./issues_raw.json
```

- 原始 issue 数据保存到 `./issues_raw.json`
- 如果 `gh` 认证失败，提示用户执行 `gh auth login`
- 获取的字段：number, title, body, labels, state, createdAt, updatedAt, comments, url, author
- 每个仓库最多获取 200 条（默认）

### 步骤 2：AI 分类

**此步骤必须由大模型亲自完成，严禁使用关键词匹配、正则表达式或任何脚本自动分类。**

读取 `./issues_raw.json`。对每条 issue，**仅**提取 `title` 和 `body`（body 取前 500 字符即可）用于分类，丢弃 labels、author、时间戳、state 等不辅助语义判断的元数据，节省 token。

逐条阅读每个 issue 的标题和描述，基于语义理解判断其是否属于值得关注的社区动向。

**属于值得关注（noteworthy）：**
- RFC / KEP / SIP / Proposal — 走正式提案流程的设计
- 架构演进 — 新子系统、重大重构、平台级变更
- 破坏性变更 — API 移除、行为变更、废弃计划
- 重大功能设计 — 有深度设计讨论的新功能提案
- 社区治理 — 策略变更、流程调整、组织变动
- 生态影响 — 影响插件、集成、下游消费者的变更
- 路线图/规划 — 追踪发布主题或长期方向的 meta issue
- 性能大改 — 涉及设计层面的性能优化
- 安全架构 — 安全模型/架构变更，非单个 CVE 修复

**不属于（routine，直接忽略）：**
- 常规 bug 修复
- 小功能请求（无设计讨论）
- 文档修正
- 依赖版本升级
- 单个 CVE/漏洞修补
- 使用问题/求助
- 小 UI 调整
- stale bot 关闭、日常维护

超过 20 条 issue 时，分批次分类，每批约 25 条。可使用并行 sub-agents 加速各批次独立分类。

分类输出要求：
- `category` **必须**使用英文代码：`rfc`、`design`、`breaking`、`governance`、`ecosystem`、`roadmap`、`perf`、`security`、`other`。报告生成时会自动转换为中文名。
- `reason` **必须**使用中文，简短描述（15-30 字），说明判断依据，如"涉及调度器插件化架构的重大重构提案"。
- `significance` 使用 `high`（需要立即关注）、`medium`（近期重要动向）、`low`（值得了解但不紧急）

输出格式——每条 issue 一个 JSON 对象：
```json
{"number":<issue号>,"is_noteworthy":true/false,"category":"<子分类|null>","significance":"high|medium|low","reason":"<中文简述>","title":"<原始标题>"}
```

分类标签：
- `rfc` — 正式 RFC/提案流程
- `design` — 架构/功能设计讨论
- `breaking` — 破坏性变更、废弃
- `governance` — 社区策略、流程、组织
- `ecosystem` — 下游/插件/集成影响
- `roadmap` — 发布主题、规划
- `perf` — 性能设计/大改
- `security` — 安全模型/架构变更
- `other` — 其他值得关注但不属于以上分类

将完整 JSON 数组写入 `./classification.json`。

### 步骤 3：生成 MD 报告

先用脚本生成报告骨架：

```bash
python3 ~/.claude/skills/github-community-insight/scripts/generate_report.py \
  --repo <owner/repo> --days <N> \
  --raw ./issues_raw.json --classify ./classification.json \
  -o docs/<repo>_insight_<timestamp>.md
```

脚本生成的骨架包含：报告头、概览统计、按分类/重要程度分布、详细 issue 表格、页脚。

**脚本执行完成后，大模型需要做的事情：**

1. 读取生成的 MD 报告文件
2. 将 `<!-- LLM_INSIGHT_PLACEHOLDER -->` 及其下一行替换为真实洞察内容
3. 基于分类结果，撰写 **"核心洞察"** 章节（2-3 段中文叙述），包含：
   - 本期社区最值得关注的 1-2 个重大动向，说明其背景和潜在影响
   - 按主题归纳其他 noteworthy issues 的共性趋势
   - 如有高重要度 issue，给出关注建议

4. 同时向用户展示摘要：

```
## 洞察结果

| 指标 | 数值 |
|------|------|
| 仓库 | <target> |
| 时间范围 | 最近 <N> 天 |
| 总 issues | <total> |
| 值得关注 | <noteworthy_count> |

### 关注分布
- 🔴 高重要度: <high_count>
- 🟡 中重要度: <medium_count>
- 🟢 低重要度: <low_count>

### 分类分布
- <category_cn>: <count>
...

📄 完整报告: docs/<repo>_insight_<timestamp>.md
```

### 步骤 4：清理

```bash
rm -f ./issues_raw.json ./classification.json
```

## 多仓库分析

多个 target 时，对每个仓库依次执行步骤 1-4。所有报告输出到同一个 `docs/` 目录下，便于集中查阅。

## 脚本

位于 `~/.claude/skills/github-community-insight/scripts/`：
- `fetch_issues.py` — 通过 `gh` CLI 获取 issue，输出原始 JSON
- `generate_report.py` — 读取 raw + classification JSON，生成 MD 报告

无需外部 Python 依赖（仅标准库）。需要安装并认证 `gh` CLI。
