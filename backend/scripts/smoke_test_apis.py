"""Smoke test key API endpoints after restart."""
from __future__ import annotations

import io
import json
import sys
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TIMEOUT = 30.0


def check(name: str, resp: httpx.Response, expect: int = 200) -> None:
    ok = resp.status_code == expect
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name} -> {resp.status_code}")
    if not ok:
        print(resp.text[:400])
        raise SystemExit(1)


def main() -> None:
    session_id = str(uuid.uuid4())
    headers: dict[str, str] = {}
    with httpx.Client(base_url=BASE, timeout=TIMEOUT) as client:
        auth_cfg = client.get("/api/auth/config").json()
        if auth_cfg.get("auth_enabled"):
            login = client.post("/api/auth/login", json={"username": "demo_member", "password": "Test123456"})
            check("auth/login", login)
            body = login.json()
            token = body.get("token")
            if not token:
                print("[FAIL] login returned no token", body)
                raise SystemExit(1)
            headers["Authorization"] = f"Bearer {token}"
            print("[OK] authenticated")

        check("system/status", client.get("/api/system/status"))
        check("experts", client.get("/api/experts", headers=headers))
        check("skills/invocable", client.get("/api/skills/invocable", headers=headers))
        check("catalog", client.get("/api/catalog"))
        check("knowledge/documents", client.get("/api/knowledge/documents", headers=headers))
        check("sessions/create", client.post("/api/sessions", json={"title": "smoke"}, headers=headers))
        check("session/context", client.get(f"/api/sessions/{session_id}/context", headers=headers))
        check(
            "session/summon",
            client.post(
                f"/api/sessions/{session_id}/summon",
                json={"expert_id": "finance_reviewer"},
                headers=headers,
            ),
        )
        ctx = client.get(f"/api/sessions/{session_id}/context", headers=headers)
        check("session/context after summon", ctx)
        data = ctx.json()
        assert data.get("expert_id") == "finance_reviewer", data
        print("[OK] summon persisted in response")

        # media upload
        png = io.BytesIO()
        try:
            from PIL import Image

            img = Image.new("RGB", (32, 32), color=(100, 100, 200))
            img.save(png, format="PNG")
        except Exception:
            png.write(b"\x89PNG\r\n\x1a\n")
            png.seek(0)
        else:
            png.seek(0)
        upload = client.post(
            "/api/media/upload",
            files={"file": ("smoke.png", png.getvalue(), "image/png")},
            headers=headers,
        )
        check("media/upload", upload)
        asset = upload.json()
        asset_id = asset.get("asset_id")
        assert asset_id, asset
        check("media/metadata", client.get(f"/api/media/{asset_id}", headers=headers))
        check("media/original", client.get(f"/api/media/{asset_id}/original", headers=headers))
        check("media/thumb", client.get(f"/api/media/{asset_id}/thumb", headers=headers), expect=200)

    print("\nAll smoke tests passed on", BASE)


if __name__ == "__main__":
    main()
