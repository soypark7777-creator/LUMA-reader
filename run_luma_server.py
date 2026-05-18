import os

from app.factory import create_app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"LUMA server starting -> http://localhost:{port}/landing")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
