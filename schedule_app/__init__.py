from flask import Flask, jsonify

def create_app() -> Flask:
    """Flask アプリを生成して返すファクトリ関数（最小構成）"""
    app = Flask(__name__)

    # ヘルスチェック用エンドポイント
    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # 暫定トップページ
    @app.get("/")
    def index():
        return "It works! 🚀", 200, {"Content-Type": "text/plain; charset=utf-8"}

    return app


# `flask --app schedule_app run` で自動検出されるエントリ
app = create_app()
