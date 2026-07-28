"""
核心配置管理模块
统一管理所有环境变量和系统配置，支持热加载
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal
from dotenv import load_dotenv

# 优先加载项目根目录 .env（避免从 backend/ 启动时读不到配置）
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env", override=True)
load_dotenv(override=True)


@dataclass
class LLMProviderConfig:
    """单个LLM Provider配置"""
    provider: str  # openai / anthropic / custom / deepseek
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ChromaDBConfig:
    host: str = "localhost"
    port: int = 8001
    persist_dir: str = "./data/chroma"
    collection_name: str = "agent_memory"

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class Neo4jConfig:
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = ""
    database: str = "neo4j"


@dataclass
class MemoryConfig:
    short_term_max_tokens: int = 4000
    long_term_top_k: int = 5
    episodic_max_events: int = 20


@dataclass
class AgentConfig:
    max_iterations: int = 10
    timeout_seconds: int = 120
    debate_max_rounds: int = 3
    default_provider: Literal["openai", "anthropic", "custom", "deepseek"] = "deepseek"


@dataclass
class AppConfig:
    """应用总配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    providers: dict[str, LLMProviderConfig] = field(default_factory=dict)
    chroma: ChromaDBConfig = field(default_factory=ChromaDBConfig)
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量构建配置"""
        providers = {}

        # DeepSeek（OpenAI 兼容接口）
        if os.getenv("DEEPSEEK_API_KEY"):
            providers["deepseek"] = LLMProviderConfig(
                provider="deepseek",
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            )

        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            providers["openai"] = LLMProviderConfig(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            )

        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            providers["anthropic"] = LLMProviderConfig(
                provider="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            )

        # Custom (Ollama / vLLM / OneAPI etc.)
        if os.getenv("CUSTOM_BASE_URL"):
            providers["custom"] = LLMProviderConfig(
                provider="custom",
                api_key=os.getenv("CUSTOM_API_KEY", "not-needed"),
                base_url=os.getenv("CUSTOM_BASE_URL", "http://localhost:11434/v1"),
                model=os.getenv("CUSTOM_MODEL", "qwen2.5:7b"),
            )

        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "true").lower() == "true",
            providers=providers,
            chroma=ChromaDBConfig(
                host=os.getenv("CHROMA_HOST", "localhost"),
                port=int(os.getenv("CHROMA_PORT", "8001")),
                persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
            ),
            neo4j=Neo4jConfig(
                uri=os.getenv("NEO4J_URI", "bolt://localhost:7688"),
                user=os.getenv("NEO4J_USER", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", ""),
                database=os.getenv("NEO4J_DATABASE", "neo4j"),
            ),
            memory=MemoryConfig(
                short_term_max_tokens=int(os.getenv("SHORT_TERM_MEMORY_MAX_TOKENS", "4000")),
                long_term_top_k=int(os.getenv("LONG_TERM_MEMORY_TOP_K", "5")),
                episodic_max_events=int(os.getenv("EPISODIC_MEMORY_MAX_EVENTS", "20")),
            ),
            agent=AgentConfig(
                max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
                timeout_seconds=int(os.getenv("AGENT_TIMEOUT_SECONDS", "120")),
                debate_max_rounds=int(os.getenv("DEBATE_MAX_ROUNDS", "3")),
                default_provider=os.getenv("DEFAULT_LLM_PROVIDER", "deepseek"),  # type: ignore[arg-type]
            ),
        )


# 全局配置单例
config = AppConfig.from_env()
