#!/usr/bin/env python3
# Harness: the loop -- the model's first connection to the real world.
"""
s01_agent_loop.py - Agent 循环

AI 编程 Agent 的全部秘密就在这个模式里：

    while stop_reason == "tool_use":
        response = LLM(messages, tools)  # 调用大模型
        execute tools                    # 执行工具
        append results                   # 把结果加回消息

    +----------+      +-------+      +---------+
    |   User   | ---> |  LLM  | ---> |  Tool   |
    |  prompt  |      |       |      | execute |
    +----------+      +---+---+      +----+----+
                          ^               |
                          |   tool_result |
                          +---------------+
                          (loop continues)

这是核心循环：把工具执行结果反馈给模型，直到模型决定停止。
生产级别的 Agent 会在这之上叠加策略、钩子和生命周期控制。
"""

# ============================================================
# 导入标准库
# ============================================================
import os      # 操作系统相关，获取环境变量等
import subprocess  # 执行外部命令

# readline 库用于增强命令行输入体验（方向键历史、Tab补全）
# 用 try 包裹是因为某些系统可能没有这个库
try:
    import readline
    # macOS libedit 的 UTF-8 退格键修复（#143）
    readline.parse_and_bind('set bind-tty-special-chars off')
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
    readline.parse_and_bind('set convert-meta off')
    readline.parse_and_bind('set enable-meta-keybindings on')
except ImportError:
    pass

# ============================================================
# 导入第三方库并初始化
# ============================================================
from openai import OpenAI          # OpenAI API 客户端
from dotenv import load_dotenv     # 从 .env 文件加载环境变量

# load_dotenv(override=True) 会读取项目根目录的 .env 文件
# 并把里面的环境变量加载到 os.environ 中
# override=True 表示如果同名变量已存在，则覆盖
load_dotenv(override=True)

# 创建 OpenAI 客户端，但这里用的是 Anthropic 的兼容接口
# base_url 和 api_key 都从环境变量读取
client = OpenAI(
    base_url=os.getenv("ANTHROPIC_BASE_URL"),   # API 基础地址
    api_key=os.getenv("ANTHROPIC_API_KEY"),     # API 密钥
)

# 使用的模型 ID，从环境变量 MODEL_ID 读取
MODEL = os.environ["MODEL_ID"]

# ============================================================
# 系统提示词
# ============================================================
# SYSTEM 是给大模型的系统提示，定义 Agent 的角色和行为
# f-string 语法：{} 里的表达式会被计算后插入字符串
SYSTEM = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

# ============================================================
# 工具定义
# ============================================================
# TOOLS 定义了大模型可以调用的工具列表
# 这里采用 OpenAI 的 function calling 格式
TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",                        # 工具名称
        "description": "Run a shell command.", # 工具描述，模型会据此判断何时调用
        "parameters": {                        # 工具的参数定义
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run"  # 参数说明
                }
            },
            "required": ["command"],           # 必需参数列表
        },
    },
}]


# ============================================================
# 工具执行函数：run_bash
# ============================================================
def run_bash(command: str) -> str:
    """
    执行 bash 命令并返回输出

    Args:
        command: 要执行的 shell 命令字符串

    Returns:
        命令的标准输出+错误输出的合并结果
    """
    # 定义危险命令列表，防止执行破坏性操作
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    # any() 检查危险命令是否出现在命令中
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"

    try:
        # subprocess.run() 执行外部命令
        # shell=True: 命令通过 shell 解析（支持管道、重定向等）
        # cwd=os.getcwd(): 在当前工作目录执行
        # capture_output=True: 捕获标准输出和标准错误
        # text=True: 返回字符串而不是字节
        # timeout=120: 120秒超时
        r = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120
        )
        # 合并 stdout 和 stderr
        out = (r.stdout + r.stderr).strip()
        # 如果有输出，截取前 50000 字符；否则返回 "(no output)"
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        # 超时异常处理
        return "Error: Timeout (120s)"


# ============================================================
# 核心模式：Agent 循环
# ============================================================
# -- The core pattern: a while loop that calls tools until the model stops --
def agent_loop(messages: list):
    """
    Agent 的核心循环

    这个函数实现了一个"工具调用循环"：
    1. 发送消息给大模型
    2. 如果大模型调用工具，执行工具并把结果加回消息
    3. 重复直到大模型不再调用工具

    Args:
        messages: 消息历史列表，大模型根据它理解上下文
                  消息格式: [{"role": "user/assistant/system", "content": "..."}]
    """
    # --------------------------------------------------------
    # 步骤1：确保系统消息存在
    # --------------------------------------------------------
    # any() 检查消息列表中是否已有 system 消息
    # 如果没有，用 insert(0, ...) 在列表开头插入系统消息
    if not any(m.get("role") == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": SYSTEM})

    # --------------------------------------------------------
    # 步骤2：进入主循环
    # --------------------------------------------------------
    while True:
        # ---- 发送请求给大模型 ----
        # client.chat.completions.create() 是调用大模型的 API
        response = client.chat.completions.create(
            model=MODEL,        # 使用的模型
            messages=messages,  # 消息历史（包含之前的所有对话）
            tools=TOOLS,        # 可用工具定义
            max_tokens=8000,    # 最大生成 token 数
        )

        # ---- 获取模型响应 ----
        # response.choices[0].message 是模型的回复消息
        msg = response.choices[0].message

        # ---- 把助手回复加入消息历史 ----
        messages.append({"role": "assistant", "content": msg.content})

        # ---- 检查模型是否调用了工具 ----
        # 如果没有 tool_calls，说明模型已经完成，直接返回
        if not msg.tool_calls:
            # 如果有文本内容（模型的最终回答），打印出来
            if msg.content:
                print(msg.content)
            return  # 退出函数

        # ---- 执行工具调用 ----
        # msg.tool_calls 是一个列表，可能有多个工具调用
        for tool_call in msg.tool_calls:
            if tool_call.function.name == "bash":
                # ---- 解析工具参数 ----
                # tool_call.function.arguments 是 JSON 字符串
                # json.loads() 把 JSON 字符串解析成 Python 字典
                import json
                args = json.loads(tool_call.function.arguments)

                # ---- 打印执行的命令（黄色）----
                # \033[33m ... \033[0m 是 ANSI 转义码，控制终端颜色
                # f-string 格式化字符串，{args['command']} 会被替换
                print(f"\033[33m$ {args['command']}\033[0m")

                # ---- 执行 bash 命令 ----
                output = run_bash(args["command"])

                # 打印输出（最多 200 字符，避免刷屏）
                print(output[:200])

                # ---- 把工具结果加入消息历史 ----
                # role="tool" 表示这是工具的返回结果
                # tool_call_id 必须与对应的 tool_call.id 匹配
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": output,
                })


# ============================================================
# 主程序入口
# ============================================================
if __name__ == "__main__":
    """
    这段代码只在直接运行本文件时执行
    如果被 import 导入，不会执行
    """
    history = []  # 对话历史列表

    # 进入主循环：不断接收用户输入
    while True:
        try:
            # input() 显示提示符并等待用户输入
            # \033[36m ... \033[0m 是青色
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D (EOF) 或 Ctrl+C (KeyboardInterrupt) 时退出
            break

        # 如果用户输入 q、exit 或空行，退出程序
        if query.strip().lower() in ("q", "exit", ""):
            break

        # ---- 把用户输入加入历史并执行 Agent 循环 ----
        history.append({"role": "user", "content": query})
        agent_loop(history)  # 调用 Agent 处理用户请求
        print()               # 打印空行分隔