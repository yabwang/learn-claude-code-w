---
name: pdf
description: 处理PDF文件——提取文本、创建PDF、合并文档。当用户要求读取PDF、创建PDF或处理PDF文件时使用。
---

# PDF 处理技能

你现在具备PDF处理的专业知识。遵循以下工作流程：

## 读取PDF

**方式1：快速文本提取（推荐）**
```bash
# 使用 pdftotext（poppler-utils）
pdftotext input.pdf -  # 输出到标准输出
pdftotext input.pdf output.txt  # 输出到文件

# 如果 pdftotext 不可用，尝试：
python3 -c "
import fitz  # PyMuPDF
doc = fitz.open('input.pdf')
for page in doc:
    print(page.get_text())
"
```

**方式2：逐页提取并获取元数据**
```python
import fitz  # pip install pymupdf

doc = fitz.open("input.pdf")
print(f"页数: {len(doc)}")
print(f"元数据: {doc.metadata}")

for i, page in enumerate(doc):
    text = page.get_text()
    print(f"--- 第 {i+1} 页 ---")
    print(text)
```

## 创建PDF

**方式1：从Markdown创建（推荐）**
```bash
# 使用 pandoc
pandoc input.md -o output.pdf

# 自定义样式
pandoc input.md -o output.pdf --pdf-engine=xelatex -V geometry:margin=1in
```

**方式2：程序化创建**
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("output.pdf", pagesize=letter)
c.drawString(100, 750, "你好，PDF！")
c.save()
```

**方式3：从HTML创建**
```bash
# 使用 wkhtmltopdf
wkhtmltopdf input.html output.pdf

# 或使用 Python
python3 -c "
import pdfkit
pdfkit.from_file('input.html', 'output.pdf')
"
```

## 合并PDF

```python
import fitz

result = fitz.open()
for pdf_path in ["file1.pdf", "file2.pdf", "file3.pdf"]:
    doc = fitz.open(pdf_path)
    result.insert_pdf(doc)
result.save("merged.pdf")
```

## 分割PDF

```python
import fitz

doc = fitz.open("input.pdf")
for i in range(len(doc)):
    single = fitz.open()
    single.insert_pdf(doc, from_page=i, to_page=i)
    single.save(f"page_{i+1}.pdf")
```

## 关键库

| 任务 | 库 | 安装 |
|------|-----|------|
| 读取/写入/合并 | PyMuPDF | `pip install pymupdf` |
| 从头创建 | ReportLab | `pip install reportlab` |
| HTML转PDF | pdfkit | `pip install pdfkit` + wkhtmltopdf |
| 文本提取 | pdftotext | `brew install poppler` / `apt install poppler-utils` |

## 最佳实践

1. **使用前检查工具是否安装**
2. **处理编码问题**——PDF可能包含各种字符编码
3. **大型PDF**：逐页处理以避免内存问题
4. **扫描版PDF**：如果文本提取返回空，使用 `pytesseract` 进行OCR