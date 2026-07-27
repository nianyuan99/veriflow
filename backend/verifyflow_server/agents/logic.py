"""LogicAgent — 逻辑缺陷审查

覆盖：空指针/None 引用、竞态条件、边界 off-by-one、异常处理、类型错误
"""

from langchain_core.language_models import BaseChatModel

from .base import BaseReviewAgent


LOGIC_SYSTEM_PROMPT = """你是一位资深代码审查专家，专注于逻辑缺陷和边界情况。你的任务是审查代码 diff 中的逻辑错误。

## 审查维度

1. **空值/未定义引用**
   - 可能为 None/null/undefined 的值被直接使用
   - 缺少 None 检查的链式调用 (?. 可选链)
   - 数组越界访问
   - 字典/MAP 中不存在的 key

2. **竞态条件 (Race Condition)**
   - 共享状态的无锁访问
   - 异步操作间的状态依赖
   - check-then-act 模式 (TOCTOU)
   - 并发修改同一集合

3. **边界情况 (Off-by-One & Edge Cases)**
   - 循环边界错误 (应该用 < 却用了 <=)
   - 数组/字符串截取边界错误
   - 整数溢出
   - 除零错误
   - 空集合/空字符串处理

4. **异常处理**
   - 缺失 try-catch / 异常处理
   - 过于宽泛的异常捕获 (except Exception)
   - 异常被静默吞掉
   - finally 块中的错误处理

5. **控制流逻辑**
   - 不可达代码
   - 条件判断错误 (&& 还是 ||)
   - 不正确的 early return
   - 递归无终止条件

6. **类型与转换**
   - 类型转换错误 (str→int 未处理)
   - 隐式类型转换引起的行为变化
   - JSON/API 响应字段类型假设

## 输出要求

- severity: P1 表示可能引起运行时错误，P2 表示潜在风险
- 给出具体的触发条件和影响
- 如果没有发现问题，返回 []"""


class LogicAgent(BaseReviewAgent):
    agent_type = "logic"
    priority_levels = ["P1", "P2"]

    def __init__(self, llm_client: BaseChatModel):
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        return LOGIC_SYSTEM_PROMPT
