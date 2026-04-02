# s03: TodoWrite (待办写入)

`s01 > s02 > [ s03 ] s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"没有计划的 agent 走哪算哪"* -- 先列步骤再动手, 完成率翻倍。
>
> **Harness 层**: 规划 -- 让模型不偏航, 但不替它画航线。

## 问题

多步任务中, 模型会丢失进度 -- 重复做过的事、跳步、跑偏。对话越长越严重: 工具结果不断填满上下文, 系统提示的影响力逐渐被稀释。一个 10 步重构可能做完 1-3 步就开始即兴发挥, 因为 4-10 步已经被挤出注意力了。

## 解决方案

```
+--------+      +-------+      +---------+
|  User  | ---> |  LLM  | ---> | Tools   |
| prompt |      |       |      | + todo  |
+--------+      +---+---+      +----+----+
                    ^                |
                    |   tool_result  |
                    +----------------+
                          |
              +-----------+-----------+
              | TodoManager state     |
              | [ ] task A            |
              | [>] task B  <- doing  |
              | [x] task C            |
              +-----------------------+
                          |
              if rounds_since_todo >= 3:
                inject <reminder> into tool_result
```

## 工作原理

1. TodoManager 存储带状态的项目。同一时间只允许一个 `in_progress`。

```python
class TodoManager:
    def update(self, items: list) -> str:
        # 规范化每条 todo，并统计 in_progress 数量（规则：同时只能有一个进行中）
        validated, in_progress_count = [], 0
        for item in items:
            status = item.get("status", "pending")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"id": item["id"], "text": item["text"],
                              "status": status})
        if in_progress_count > 1:
            raise ValueError("Only one task can be in_progress")
        self.items = validated
        # 返回渲染后的文本，作为 tool_result 回给模型，便于下一轮继续对齐计划
        return self.render()
```

2. `todo` 工具和其他工具一样加入 dispatch map。

```python
# 与 s02 相同：按工具名分发；todo 的入参是模型生成的 items 列表
TOOL_HANDLERS = {
    # ...base tools...
    "todo": lambda **kw: TODO.update(kw["items"]),
}
```

3. nag reminder: 模型连续 3 轮以上不调用 `todo` 时注入提醒。

```python
# rounds_since_todo：自上次调用 todo 工具以来的轮次，由循环维护
if rounds_since_todo >= 3 and messages:
    last = messages[-1]
    # 仅当最后一条是「带多段 content 的 user」（例如紧跟 tool_results）时插入提醒块
    if last["role"] == "user" and isinstance(last.get("content"), list):
        # 插在列表最前，让模型优先看到，又不破坏原有 tool_result 块顺序
        last["content"].insert(0, {
            "type": "text",
            "text": "<reminder>Update your todos.</reminder>",
        })
```

"同时只能有一个 in_progress" 强制顺序聚焦。nag reminder 制造问责压力 -- 你不更新计划, 系统就追着你问。

## 相对 s02 的变更

| 组件           | 之前 (s02)       | 之后 (s03)                     |
|----------------|------------------|--------------------------------|
| Tools          | 4                | 5 (+todo)                      |
| 规划           | 无               | 带状态的 TodoManager           |
| Nag 注入       | 无               | 3 轮后注入 `<reminder>`        |
| Agent loop     | 简单分发         | + rounds_since_todo 计数器     |

## 试一试

```sh
cd learn-claude-code
python agents/s03_todo_write.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Refactor the file hello.py: add type hints, docstrings, and a main guard`
2. `Create a Python package with __init__.py, utils.py, and tests/test_utils.py`
3. `Review all Python files and fix any style issues`
