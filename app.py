"""
LUMA — AI 독서 소셜 플랫폼
실행: python app.py
접속: http://localhost:5000/landing
"""
import sys, os
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from app.factory import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n🌿 LUMA 서버 시작 → http://localhost:{port}/landing\n")
    app.run(host="0.0.0.0", port=port, debug=True)
