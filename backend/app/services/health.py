"""System health and status probes"""
from app.core.config import config
from app.db.chroma import get_chroma_client
from app.db.neo4j import get_neo4j_client
from app.llm.factory import LLMFactory


def probe_chroma() -> dict:
    try:
        client = get_chroma_client()
        try:
            count = client.count("knowledge_base")
        except Exception:
            count = 0
        return {"status": "up", "mode": "remote" if client.is_remote else "local", "docs": count}
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


def probe_neo4j() -> dict:
    client = get_neo4j_client()
    if not client.available:
        return {"status": "down", "error": "Neo4j unavailable"}
    try:
        return {
            "status": "up",
            "entities": client.count_entities(),
            "documents": client.count_documents(),
        }
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


def probe_llm() -> dict:
    providers = []
    for p in LLMFactory.list_providers():
        name = p["name"]
        cfg = config.providers.get(name)
        providers.append({
            **p,
            "has_api_key": bool(cfg and cfg.api_key and cfg.api_key not in ("", "not-needed", "sk-your-key-here")),
        })
    default = config.agent.default_provider
    return {"status": "up" if providers else "down", "default_provider": default, "providers": providers}


async def probe_mysql() -> dict:
    from app.core.database import ping_mysql
    return await ping_mysql()


async def probe_redis() -> dict:
    from app.db.redis_client import ping_redis
    return await ping_redis()


async def get_system_status() -> dict:
    chroma = probe_chroma()
    neo4j = probe_neo4j()
    llm = probe_llm()
    mysql = await probe_mysql()
    redis = await probe_redis()
    overall = "healthy"
    if chroma["status"] != "up" or llm["status"] != "up":
        overall = "degraded"
    if mysql["status"] != "up":
        overall = "degraded"
    if chroma["status"] != "up" and neo4j["status"] != "up":
        overall = "unhealthy"
    return {
        "status": overall,
        "mysql": mysql,
        "redis": redis,
        "chroma": chroma,
        "neo4j": neo4j,
        "llm": llm,
    }
