#!/usr/bin/env python3
# Harness: tool dispatch -- expanding what the model can reach.
"""
s02_tool_use.py - Tools

The agent loop from s01 didn't change. We just added tools to the array
and a dispatch map to route calls.

    +----------+      +-------+      +------------------+
    |   User   | ---> |  LLM  | ---> | Tool Dispatch    |
    |  prompt  |      |       |      | {                |
    +----------+      +---+---+      |   bash: run_bash |
                          ^          |   read: run_read |
                          |          |   write: run_wr  |
                          +----------+   edit: run_edit |
                          tool_result| }                |
                                     +------------------+

Key insight: "The loop didn't change at all. I just added tools."
"""

# ============================================================
# 自动检测并使用虚拟环境
# ============================================================
import sys
import os
from pathlib import Path

# 查找项目根目录的 .venv
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
_venv_path = _project_root / ".venv"

if _venv_path.exists() and not os.environ.get("VIRTUAL_ENV"):
    # 添加虚拟环境的 site-packages 到 sys.path
    _site_packages = _venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if _site_packages.exists():
        sys.path.insert(0, str(_site_packages))

import subprocess
import json

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
    readline.parse_and_bind('set enable-meta-keybindings on')
except ImportError:
    pass

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# 工作区根目录：所有 read/write/edit 路径均相对于此，并由 safe_path 约束不可逃逸
WORKDIR = Path.cwd()
# OpenAI 兼容接口：可用 Anthropic 兼容网关，凭 ANTHROPIC_* 环境变量连接
client = OpenAI(
    base_url=os.getenv("ANTHROPIC_BASE_URL"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


def safe_path(p: str) -> Path:
    # 解析为绝对路径后必须仍落在 WORKDIR 下，防止 ../ 等跳出沙箱
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    # 教学用简单黑名单；生产环境应更强策略（白名单、隔离执行等）
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        # cwd 固定在工作区，命令在子进程中执行
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"  # 截断避免撑爆上下文
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        # limit：只读前 N 行，并提示剩余行数
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]  # 总字符上限，与 bash 输出一致
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)  # 允许写入嵌套新路径
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        # replace(..., 1) 只替换第一处，避免误改多处相同片段
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


# 工具名 -> 可调用对象；与 TOOLS 里 function.name 一致，循环里按名查找即可
TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": lambda args: run_read(args["path"], args.get("limit")),
    "write_file": lambda args: run_write(args["path"], args["content"]),
    "edit_file": lambda args: run_edit(args["path"], args["old_text"], args["new_text"]),
}

# OpenAI Chat Completions 的 tools 格式；模型据此生成 tool_calls
TOOLS = [
    {"type": "function", "function": {
        "name": "bash",
        "description": "Run a shell command.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The shell command to run"}},
            "required": ["command"],
        },
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read file contents.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
                "limit": {"type": "integer", "description": "Max lines to read"},
            },
            "required": ["path"],
        },
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Write content to file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    }},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Replace exact text in file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to workspace"},
                "old_text": {"type": "string", "description": "Text to find and replace"},
                "new_text": {"type": "string", "description": "Replacement text"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    }},
]


def agent_loop(messages: list):
    """Agent 核心循环 - 使用 OpenAI SDK 格式"""
    # 首轮注入 system，与 s01 行为一致（历史里可多次 user/assistant/tool）
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": SYSTEM})

    while True:
        response = client.chat.completions.create(
            model=MODEL, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        msg = response.choices[0].message
        # 必须原样保留 assistant 消息（含 tool_calls），下一轮模型才能对上工具结果
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        # 无 tool_calls = 模型给出最终文本，结束本轮对话
        if not msg.tool_calls:
            if msg.content:
                print(msg.content)
            return

        # 每个 tool_call 对应一条 role=tool 消息，tool_call_id 必须与请求一致
        for tool_call in msg.tool_calls:
            handler = TOOL_HANDLERS.get(tool_call.function.name)
            args = json.loads(tool_call.function.arguments)
            output = handler(args) if handler else f"Unknown tool: {tool_call.function.name}"
            print(f"\033[33m> {tool_call.function.name}\033[0m")
            print(output[:200])  # 终端只预览前 200 字符，完整内容写入 messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": output,
            })


if __name__ == "__main__":
    # 跨多轮 input 复用同一条 message 列表，实现连续对话上下文
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)  # 内部可能多轮 LLM+工具，直到无 tool_calls 才返回
        print()