"""Pre-deploy smoke checks for LUMA pages and APIs."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


PAGES = [
    "/",
    "/heart",
    "/lounge",
    "/social",
    "/community/",
    "/ocr",
    "/deepdive",
    "/socrates",
    "/live",
    "/profile",
    "/auth/login",
]

APIS = [
    "/api/v2/system/status",
    "/api/v2/shelf?user_id=user_demo",
    "/api/v2/social/feed?user_id=user_demo&limit=3",
    "/api/ocr/status",
    "/ocr/health",
    "/api/v2/community/clubs?user_id=user_demo",
]


def fetch(url: str, timeout: int) -> tuple[int, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "LUMA-preflight/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, response.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, exc.headers.get("Content-Type", ""), body
    except Exception as exc:
        return 0, "", str(exc)


def check_page(base_url: str, path: str, timeout: int) -> dict:
    status, content_type, body = fetch(base_url + path, timeout)
    nav_count = body.count("class=\"topbar") + body.count("class='topbar")
    login_markers = ["로그인", "로그아웃", "nav-user", "auth/login"]
    return {
        "path": path,
        "status": status,
        "ok": status == 200,
        "content_type": content_type,
        "topbar_markers": nav_count,
        "has_auth_marker": any(marker in body for marker in login_markers),
        "body_len": len(body),
    }


def check_api(base_url: str, path: str, timeout: int) -> dict:
    status, content_type, body = fetch(base_url + path, timeout)
    parsed = None
    if "json" in content_type.lower() or body.strip().startswith("{"):
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = None
    api_ok = status == 200 and (parsed is None or parsed.get("ok", True) is not False)
    return {
        "path": path,
        "status": status,
        "ok": api_ok,
        "content_type": content_type,
        "json_ok": parsed.get("ok") if isinstance(parsed, dict) else None,
        "source": parsed.get("source") if isinstance(parsed, dict) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5000")
    parser.add_argument("--timeout", type=int, default=8)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    page_results = [check_page(base_url, path, args.timeout) for path in PAGES]
    api_results = [check_api(base_url, path, args.timeout) for path in APIS]

    print("== Pages ==")
    for item in page_results:
        flag = "OK" if item["ok"] else "FAIL"
        print(f"{flag:4} {item['status']:>3} {item['path']:<18} topbar={item['topbar_markers']} auth={item['has_auth_marker']}")

    print("\n== APIs ==")
    for item in api_results:
        flag = "OK" if item["ok"] else "FAIL"
        print(f"{flag:4} {item['status']:>3} {item['path']:<46} json_ok={item['json_ok']} source={item['source']}")

    failed = [item for item in page_results + api_results if not item["ok"]]
    if failed:
        print("\nFailed checks:")
        for item in failed:
            print(f"- {item['path']} status={item['status']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
