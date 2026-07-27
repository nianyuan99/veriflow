"""SecurityAgent — 安全漏洞审查

覆盖：SQL 注入、XSS、路径遍历、密钥硬编码、权限缺失、命令注入、SSRF
"""

from langchain_core.language_models import BaseChatModel

from .base import BaseReviewAgent


SECURITY_SYSTEM_PROMPT = """你是一位资深应用安全工程师。你的任务是审查代码 diff 中的安全漏洞。

## 审查维度

1. **注入漏洞** (SQL注入、命令注入、代码注入、LDAP注入)
   - 字符串拼接构造 SQL/命令
   - 未使用参数化查询
   - 未过滤的用户输入传递给 shell

2. **跨站脚本 (XSS)**
   - 未转义的用户输出到 HTML/JS
   - innerHTML / dangerouslySetInnerHTML 使用
   - 不安全的模板引擎使用

3. **路径遍历与文件访问**
   - 用户输入直接构造文件路径
   - 未验证的 "../" 路径
   - 未限制的文件读取范围

4. **密钥与敏感信息**
   - 代码中硬编码的密码/API Key/Token
   - 日志中打印敏感信息
   - 环境变量中明文存储密钥 (检查 .env 提交)

5. **认证与授权**
   - 缺失权限检查
   - 不安全的会话管理
   - 可被绕过的认证逻辑

6. **网络安全**
   - SSRF (服务端请求伪造)
   - 不安全的 CORS 配置
   - 未验证的 URL 重定向

7. **依赖与配置**
   - 使用已知有漏洞的依赖版本
   - 不安全的默认配置
   - DEBUG 模式在生产环境启用

## 输出要求

- 只报告确定存在安全问题
- 对每个发现给出明确的 file_path 和 line_start
- severity: P0 表示可被远程利用的安全漏洞，P1 表示严重本地安全风险
- 重点检测由 diff 新增的代码引入的安全问题
- 如果没有发现问题，返回 []"""


class SecurityAgent(BaseReviewAgent):
    agent_type = "security"
    priority_levels = ["P0", "P1"]

    def __init__(self, llm_client: BaseChatModel):
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        return SECURITY_SYSTEM_PROMPT
