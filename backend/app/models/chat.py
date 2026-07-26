"""聊天相关数据模型"""
from pydantic import BaseModel
from typing import Optional, Literal


class ChatRequest(BaseModel):
    """聊天请求"""
    input: str
    session_id: Optional[str] = None
    provider: str = "deepseek"
    model: Optional[str] = None
    mode: Literal["react", "plan_execute", "multi_agent", "auto"] = "auto"
    skill: Optional[str] = None  # 激活的技能名称
    temperature: float = 0.7


class ChatResponse(BaseModel):
    """聊天响应"""
    output: str
    session_id: str
    tool_calls: list[dict] = []
    execution_time_ms: float = 0


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    message_count: int
    created_at: str = ""
    last_active: str = ""
