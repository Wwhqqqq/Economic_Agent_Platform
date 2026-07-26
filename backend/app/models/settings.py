"""设置数据模型"""
from pydantic import BaseModel
from typing import Optional


class LLMProviderUpdate(BaseModel):
    """LLM Provider 更新请求"""
    provider: str  # deepseek / openai / anthropic / custom
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class KnowledgeUpload(BaseModel):
    """知识库上传"""
    content: str
    doc_id: Optional[str] = None
    metadata: Optional[dict] = None
    entities: Optional[list[dict]] = None


class KnowledgeSearch(BaseModel):
    """知识库检索"""
    query: str
    top_k: int = 5
    mode: str = "hybrid"  # vector / graph / hybrid


class SkillExecuteRequest(BaseModel):
    """技能执行请求"""
    input: str
    session_id: str = "default"
    temperature: float = 0.7
    provider: Optional[str] = None
    model: Optional[str] = None
