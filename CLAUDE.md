# Learn Claude Code 学习指南

## 仓库概述

这是一个教你**构建 Agent Harness（智能代理运行环境）**的教学项目，逆向拆解了 Claude Code 的核心架构。

核心概念：
- **Agent 是模型本身**（Claude/GPT 等）
- **Harness 是工程师构建的**（工具、知识、上下文管理、权限等）

学习目标是：如何为 AI 模型构建一个"工作环境"，让它能有效执行任务。

---

## 学习路径

### 第一阶段：基础循环

| 课程 | 主题 | 格言 | 文档 |
|------|------|------|------|
| s01 | Agent Loop | *One loop & Bash is all you need* | docs/zh/s01-the-agent-loop.md |
| s02 | Tool Use | *加一个工具, 只加一个 handler* | docs/zh/s02-tool-use.md |

### 第二阶段：规划与知识管理

| 课程 | 主题 | 格言 | 文档 |
|------|------|------|------|
| s03 | TodoWrite | *没有计划的 agent 走哪算哪* | docs/zh/s03-todo-write.md |
| s04 | Subagent | *大任务拆小, 每个小任务干净的上下文* | docs/zh/s04-subagent.md |
| s05 | Skill Loading | *用到什么知识, 临时加载什么知识* | docs/zh/s05-skill-loading.md |
| s06 | Context Compact | *上下文总会满, 要有办法腾地方* | docs/zh/s06-context-compact.md |

### 第三阶段：持久化

| 课程 | 主题 | 格言 | 文档 |
|------|------|------|------|
| s07 | Task System | *大目标要拆成小任务, 排好序, 记在磁盘上* | docs/zh/s07-task-system.md |
| s08 | Background Tasks | *慢操作丢后台, agent 继续想下一步* | docs/zh/s08-background-tasks.md |

### 第四阶段：团队协作

| 课程 | 主题 | 格言 | 文档 |
|------|------|------|------|
| s09 | Agent Teams | *任务太大一个人干不完, 要能分给队友* | docs/zh/s09-agent-teams.md |
| s10 | Team Protocols | *队友之间要有统一的沟通规矩* | docs/zh/s10-team-protocols.md |
| s11 | Autonomous Agents | *队友自己看看板, 有活就认领* | docs/zh/s11-autonomous-agents.md |
| s12 | Worktree Isolation | *各干各的目录, 互不干扰* | docs/zh/s12-worktree-task-isolation.md |

---

## 实践步骤

### 1. 文档阅读
每个课程先读文档建立心智模型，文档位于 `docs/zh/` 目录。

### 2. 运行代码
按顺序运行示例代码：

```bash
# 基础
python agents/s01_agent_loop.py
python agents/s02_tool_use.py

# 规划与知识
python agents/s03_todo_write.py
python agents/s04_subagent.py
python agents/s05_skill_loading.py
python agents/s06_context_compact.py

# 持久化
python agents/s07_task_system.py
python agents/s08_background_tasks.py

# 团队协作
python agents/s09_agent_teams.py
python agents/s10_team_protocols.py
python agents/s11_autonomous_agents.py
python agents/s12_worktree_task_isolation.py

# 完整实现
python agents/s_full.py
```

### 3. Web 平台（可选）
交互式可视化学习：

```bash
cd web && npm install && npm run dev
# 访问 http://localhost:3000
```

---

## 学习顺序总结

```
文档阅读 → 代码运行 → 理解模式 → 修改实验
```

---

## 核心代码模式

```python
def agent_loop(messages):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM,
            messages=messages, tools=TOOLS,
        )
        messages.append({"role": "assistant",
                         "content": response.content})

        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = TOOL_HANDLERS[block.name](**block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})
```

每个课程在这个循环之上叠加一个 harness 机制，循环本身始终不变。

---

## Harness 工程哲学（必读）

> **模型已经知道如何成为 agent。你的工作是给它构建一个值得栖居的世界。**

### 核心真理

Agent 不是代码。Agent 是模型本身——一个经过数十亿次梯度更新训练的神经网络，学会了感知环境、推理目标、采取行动。

代码是 harness。模型是 agent。混淆二者，就会构建错误的东西。

### Agent 是什么

- **人类**：生物神经网络，进化训练
- **DeepMind DQN**：卷积网络，从像素学习玩 Atari
- **OpenAI Five**：五个网络，通过自我对弈学习 Dota 2 团队协作
- **Claude**：语言模型，从人类知识中学习推理和行动

Agent 永远是训练好的模型。不是游戏引擎，不是终端，不是框架。

### Agent 不是什么

用 if-else 分支、节点图、硬编码路由把 LLM API 调用串起来，不产生 agent。那产生的是脆弱的流水线——一个把 LLM 塞进去当文本补全节点的鲁布·戈德堡机械。

**Agency 是学出来的，不是编出来的。** 没有任何胶水代码能涌现出自主行为。

### Harness 的五大要素

```
Harness = Tools + Knowledge + Context + Permissions + Task-Process Data
```

| 要素 | 问题 | 设计原则 |
|------|------|----------|
| **Tools** | Agent 能做什么？ | 原子化、可组合、描述清晰。从 3-5 个开始 |
| **Knowledge** | Agent 知道什么？ | 按需加载（tool_result），不要前置塞入 |
| **Context** | Agent 记住什么？ | 保护上下文。隔离噪声子任务。压缩冗长历史 |
| **Permissions** | Agent 允许做什么？ | 约束聚焦行为，而非限制行为 |
| **Task-Process Data** | Agent 的训练信号 | 每条行动序列都是微调下一代模型的原材料 |

### 渐进复杂度

```
Level 0: Model + bash                           -- s01
Level 1: Model + tool dispatch                  -- s02
Level 2: Model + planning                       -- s03
Level 3: Model + subagents + skills             -- s04, s05
Level 4: Model + context + persistence          -- s06, s07, s08
Level 5: Model + teams + autonomy + isolation   -- s09-s12
```

从最低可能有效的层级开始。只有真实使用揭示需求时才向上移动。

### Harness 工程原则

1. **信任模型** —— 模型比你写的规则系统更擅长推理
2. **约束使能** —— 约束防止模型迷失，而非微观管理
3. **渐进复杂** —— 从简入繁，按需演进

### 思维转换

| 从 | 到 |
|----|----|
| "如何让系统做 X？" | "如何让模型能做 X？" |
| "用户说 Y 时该发生什么？" | "什么工具能帮助处理 Y？" |
| "这个任务的流程是什么？" | "模型需要什么才能自己推导流程？" |
| "我在构建 agent" | "我在为 agent 构建 harness" |

### 车辆隐喻

模型是驾驶员。Harness 是车辆。

- 编程 agent 的车辆：IDE、终端、文件系统
- 农业 agent 的车辆：传感器、灌溉控制、气象数据
- 酒店 agent 的车辆：预订系统、客户通道、设施 API

驾驶员泛化。车辆专化。Harness 工程师的职责是为领域构建最好的车辆——给驾驶员最大视野、精确控制、清晰边界。

**造好 Harness，Agent 会完成剩下的。**

---

## 其他重要文件

| 文件 | 内容 | 阅读时机 |
|------|------|----------|
| `skills/agent-builder/SKILL.md` | Agent 构建设计原则 | 学完 s01-s06 后 |
| `skills/mcp-builder/SKILL.md` | MCP 服务器构建指南 | 想扩展 Claude 能力时 |
| `agents/s_full.py` | 全部机制合一的完整实现 | 学完所有课程后深入 |
| `.env.example` | 多模型提供商配置（GLM/DeepSeek 等） | 配置环境时 |

---

## 推荐阅读优先级

```
必读（现在）:
  → skills/agent-builder/references/agent-philosophy.md

按课程进度:
  → docs/zh/s01-s12 + agents/s01-s12.py

学完后深入:
  → agents/s_full.py
  → skills/agent-builder/SKILL.md

扩展时参考:
  → skills/mcp-builder/SKILL.md
```

---

## 开发规则

### Python 脚本运行

所有 `agents/` 目录下的 Python 脚本必须支持直接运行（无需手动激活虚拟环境）：

```bash
python3 agents/s01_agent_loop.py
python3 agents/s02_tool_use.py
```

脚本开头需包含虚拟环境自动检测代码：

```python
import sys
import os
from pathlib import Path

# 查找项目根目录的 .venv
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
_venv_path = _project_root / ".venv"

if _venv_path.exists() and not os.environ.get("VIRTUAL_ENV"):
    _site_packages = _venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if _site_packages.exists():
        sys.path.insert(0, str(_site_packages))
```

### API 配置

本项目使用阿里云 DashScope API（OpenAI 兼容格式）：

| 配置项 | 值 |
|--------|-----|
| `ANTHROPIC_BASE_URL` | `https://coding.dashscope.aliyuncs.com/v1` |
| `ANTHROPIC_API_KEY` | DashScope API Key |
| `MODEL_ID` | `glm-5` |

**注意**：DashScope 使用 OpenAI SDK 格式，不是 Anthropic SDK。脚本需使用：

```python
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("ANTHROPIC_BASE_URL"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)
```

### 依赖管理

- 虚拟环境目录：`.venv/`
- 依赖文件：`requirements.txt`
- 安装依赖：`source .venv/bin/activate && pip install -r requirements.txt`