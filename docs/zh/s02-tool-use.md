# s02: Tool Use (工具使用)

`s01 > [ s02 ] s03 > s04 > s05 > s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"加一个工具, 只加一个 handler"* -- 循环不用动, 新工具注册进 dispatch map 就行。
>
> **Harness 层**: 工具分发 -- 扩展模型能触达的边界。

## 问题

只有 `bash` 时, 所有操作都走 shell。`cat` 截断不可预测, `sed` 遇到特殊字符就崩, 每次 bash 调用都是不受约束的安全面。专用工具 (`read_file`, `write_file`) 可以在工具层面做路径沙箱。

关键洞察: 加工具不需要改循环。

## 解决方案

```
+--------+      +-------+      +------------------+
|  User  | ---> |  LLM  | ---> | Tool Dispatch    |
| prompt |      |       |      | {                |
+--------+      +---+---+      |   bash: run_bash |
                    ^           |   read: run_read |
                    |           |   write: run_wr  |
                    +-----------+   edit: run_edit |
                    tool_result | }                |
                                +------------------+

The dispatch map is a dict: {tool_name: handler_function}.
One lookup replaces any if/elif chain.
```

## 工作原理

1. 每个工具有一个处理函数。路径沙箱防止逃逸工作区。

```python
def safe_path(p: str) -> Path:
    # 相对工作区解析路径，禁止 ../ 等逃逸到工作区外
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_read(path: str, limit: int = None) -> str:
    text = safe_path(path).read_text()
    lines = text.splitlines()
    # 可选：只返回前 limit 行，避免大文件撑爆上下文
    if limit and limit < len(lines):
        lines = lines[:limit]
    # 截断总字符数，与常见 agent 读文件上限一致
    return "\n".join(lines)[:50000]
```

2. dispatch map 将工具名映射到处理函数。

```python
# 工具名 -> 处理函数；LLM 的 tool_use.name 在此查找，无需改循环里的 if/elif
TOOL_HANDLERS = {
    "bash":       lambda **kw: run_bash(kw["command"]),
    "read_file":  lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":  lambda **kw: run_edit(kw["path"], kw["old_text"],
                                        kw["new_text"]),
}
```

3. 循环中按名称查找处理函数。循环体本身与 s01 完全一致。

```python
for block in response.content:
    if block.type == "tool_use":
        # 按名称分发；未注册则返回可读错误，仍走同一套 tool_result 回传
        handler = TOOL_HANDLERS.get(block.name)
        output = handler(**block.input) if handler \
            else f"Unknown tool: {block.name}"
        # 与 s01 相同：把结果挂回 tool_use_id，供下一轮模型消费
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": output,
        })
```

加工具 = 加 handler + 加 schema。循环永远不变。

## 相对 s01 的变更

| 组件           | 之前 (s01)         | 之后 (s02)                     |
|----------------|--------------------|--------------------------------|
| Tools          | 1 (仅 bash)        | 4 (bash, read, write, edit)    |
| Dispatch       | 硬编码 bash 调用   | `TOOL_HANDLERS` 字典           |
| 路径安全       | 无                 | `safe_path()` 沙箱             |
| Agent loop     | 不变               | 不变                           |

## 试一试

```sh
cd learn-claude-code
python agents/s02_tool_use.py
```

试试这些 prompt (英文 prompt 对 LLM 效果更好, 也可以用中文):

1. `Read the file requirements.txt`
2. `Create a file called greet.py with a greet(name) function`
3. `Edit greet.py to add a docstring to the function`
4. `Read greet.py to verify the edit worked`
