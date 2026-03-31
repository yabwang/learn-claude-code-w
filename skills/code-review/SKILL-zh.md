---
name: code-review
description: 执行全面的代码审查，包括安全性、性能和可维护性分析。当用户要求审查代码、检查错误或审计代码库时使用。
---

# 代码审查技能

你现在具备进行全面代码审查的专业知识。请遵循以下结构化方法：

## 审查清单

### 1. 安全性（关键）

检查以下内容：
- [ ] **注入漏洞**：SQL注入、命令注入、XSS、模板注入
- [ ] **认证问题**：硬编码凭据、弱认证
- [ ] **授权缺陷**：缺失访问控制、IDOR（不安全的直接对象引用）
- [ ] **数据泄露**：日志中的敏感数据、错误消息泄露
- [ ] **加密问题**：弱算法、不当的密钥管理
- [ ] **依赖漏洞**：已知漏洞（使用 `npm audit`、`pip-audit` 检查）

```bash
# 快速安全扫描
npm audit                    # Node.js
pip-audit                    # Python
cargo audit                  # Rust
grep -r "password\|secret\|api_key" --include="*.py" --include="*.js"
```

### 2. 正确性

检查以下内容：
- [ ] **逻辑错误**：边界偏差、空值处理、边缘情况
- [ ] **竞态条件**：无同步的并发访问
- [ ] **资源泄漏**：未关闭的文件、连接、内存
- [ ] **错误处理**：吞掉的异常、缺失的错误路径
- [ ] **类型安全**：隐式转换、any类型滥用

### 3. 性能

检查以下内容：
- [ ] **N+1查询**：循环中的数据库调用
- [ ] **内存问题**：大内存分配、保留的引用
- [ ] **阻塞操作**：异步代码中的同步I/O
- [ ] **低效算法**：能用O(n)时却用O(n²)
- [ ] **缺失缓存**：重复的昂贵计算

### 4. 可维护性

检查以下内容：
- [ ] **命名**：清晰、一致、描述性强
- [ ] **复杂度**：函数超过50行、嵌套深度超过3层
- [ ] **重复**：复制粘贴的代码块
- [ ] **死代码**：未使用的导入、不可达分支
- [ ] **注释**：过时、冗余或缺失必要的注释

### 5. 测试

检查以下内容：
- [ ] **覆盖率**：关键路径是否被测试
- [ ] **边缘情况**：空值、空值、边界值
- [ ] **Mock**：外部依赖是否被隔离
- [ ] **断言**：有意义、具体的检查

## 审查输出格式

```markdown
## 代码审查：[文件/组件名称]

### 概述
[1-2句话总体描述]

### 关键问题
1. **[问题]**（第X行）：[描述]
   - 影响：[可能出什么问题]
   - 修复：[建议的解决方案]

### 改进建议
1. **[建议]**（第X行）：[描述]

### 良好之处
- [做得好的地方]

### 结论
[ ] 可以合并
[ ] 需要小修改
[ ] 需要大修改
```

## 常见问题模式

### Python
```python
# 错误：SQL注入
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# 正确：
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# 错误：命令注入
os.system(f"ls {user_input}")
# 正确：
subprocess.run(["ls", user_input], check=True)

# 错误：可变默认参数
def append(item, lst=[]):  # Bug：共享的可变默认值
# 正确：
def append(item, lst=None):
    lst = lst or []
```

### JavaScript/TypeScript
```javascript
// 错误：原型污染
Object.assign(target, userInput)
// 正确：
Object.assign(target, sanitize(userInput))

// 错误：eval使用
eval(userCode)
// 正确：永远不要对用户输入使用eval

// 错误：回调地狱
getData(x => process(x, y => save(y, z => done(z))))
// 正确：
const data = await getData();
const processed = await process(data);
await save(processed);
```

## 审查命令

```bash
# 显示最近的更改
git diff HEAD~5 --stat
git log --oneline -10

# 查找潜在问题
grep -rn "TODO\|FIXME\|HACK\|XXX" .
grep -rn "password\|secret\|token" . --include="*.py"

# 检查复杂度（Python）
pip install radon && radon cc . -a

# 检查依赖
npm outdated  # Node
pip list --outdated  # Python
```

## 审查工作流程

1. **理解上下文**：阅读PR描述、关联的issue
2. **运行代码**：构建、测试、尽可能本地运行
3. **从上往下阅读**：从主要入口点开始
4. **检查测试**：改动是否被测试？测试是否通过？
5. **安全扫描**：运行自动化工具
6. **人工审查**：使用上面的清单
7. **编写反馈**：具体、建议修复方案、友善