# VerifyFlow

AI 代码审查 Agent + 沙箱验证闭环 + Obsidian 知识沉淀

## 三大差异化竞争力

| 能力 | 说明 |
|------|------|
| 沙箱验证闭环 | fix → Docker → test → pass/fail，无人做过 |
| Benchmark 驱动质量量化 | precision/recall/F1 评分 |
| Obsidian 错误知识库自动沉淀 | 审查结果自动存入知识库 |

## 技术栈

- **后端**: Python 3.11+ / FastAPI / LangGraph / SQLAlchemy + SQLite
- **前端**: React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS
- **沙箱**: Docker SDK for Python
- **代码分析**: Tree-sitter + Semgrep

## 快速开始

```bash
# 后端
cd backend
pip install -e .
uvicorn verifyflow_server.main:app --port 8710

# 前端
cd frontend
npm install
npm run dev

# CLI
cd cli
pip install -e .
verifyflow review --diff example.patch
```

## 项目结构

```
verifyflow/
├── cli/          # Typer CLI 工具
├── backend/      # FastAPI + LangGraph 后端
├── frontend/     # React Dashboard
└── docs/         # 文档
```
