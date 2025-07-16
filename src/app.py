# src/app.py

# eventletのモンキーパッチを最初に適用
import eventlet

eventlet.monkey_patch()

import logging
import os
from threading import Lock

# ★★★ render_template をインポート ★★★
from flask import Flask, render_template
from flask_socketio import SocketIO

from src.camera_control import init_raspi_camera
from src.config import config
from src.recognition.worker import face_recognition_worker
from src.streaming.receiver import StreamReceiver

# --- グローバル変数と設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(process)d] - %(message)s",
)
# ★★★ Flaskインスタンス化時にテンプレートと静的ファイルのディレクトリを自動で認識 ★★★
app = Flask(__name__, template_folder="templates", static_folder="static")
sio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# ワーカーの初期化が一度だけ実行されることを保証するためのロック
worker_setup_lock = Lock()
worker_initialized = False


# --- ワーカープロセスの初期化 ---
def setup_worker_resources():
    """Gunicornの各ワーカープロセスで一度だけ実行される初期化処理"""
    global worker_initialized
    if worker_initialized:
        return
    with worker_setup_lock:
        if worker_initialized:
            return

        logging.info(f"ワーカープロセス {os.getpid()} の初期化を開始します...")
        init_raspi_camera()
        stream_receiver = StreamReceiver(config.RASPI_STREAM_URL)
        sio.start_background_task(face_recognition_worker, sio, stream_receiver)
        logging.info(f"ワーカープロセス {os.getpid()} の初期化が完了しました。")
        worker_initialized = True


# --- ルートとSocket.IOイベントハンドラ ---
@app.route("/")
def index():
    """
    クライアントに表示するHTMLをレンダリングする
    """
    # 最初のリクエスト時にワーカーの初期化をトリガー
    setup_worker_resources()
    # ★★★ `render_template` を使って外部HTMLファイルをレンダリング ★★★
    return render_template("index.html", stream_url=config.RASPI_STREAM_URL)


@sio.on("connect", namespace="/live")
def on_connect():
    """最初のクライアント接続時にワーカーの初期化をトリガー"""
    setup_worker_resources()
    logging.info("クライアントが接続しました。")
