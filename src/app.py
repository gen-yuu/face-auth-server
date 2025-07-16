# eventletのモンキーパッチを最初に適用
import eventlet

eventlet.monkey_patch()

import atexit
import logging
import os
from threading import Lock

from flask import Flask, Response, render_template
from flask_socketio import SocketIO

# ★★★ configを最初にインポート ★★★
from src.config import config
from src.recognition.worker import face_recognition_worker
from src.streaming.receiver import StreamReceiver

# --- モードに応じたインポートと設定 ---
if config.IS_DEVELOPMENT_MODE:
    # 開発モード用のモジュールをインポート
    from src.camera_dev import generate_frames, initialize_dev_camera

    logging.info("【開発モード】でアプリケーションを起動します。")
else:
    # 本番モード用のモジュールをインポート
    from src.camera_control import init_raspi_camera, release_raspi_camera

    logging.info("【本番モード】でアプリケーションを起動します。")

# --- グローバル変数と設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(process)d] - %(message)s",
)
app = Flask(__name__, template_folder="templates", static_folder="static")
sio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

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

        if config.IS_DEVELOPMENT_MODE:
            # --- 開発モードのカメラ初期化 ---
            initialize_dev_camera()
        else:
            # --- 本番モードのカメラ初期化 ---
            init_raspi_camera()
            atexit.register(release_raspi_camera)

        # 顔認証ワーカーをバックグラウンドで開始 (STREAM_URLはconfigが自動で選択)
        stream_receiver = StreamReceiver(config.STREAM_URL)
        sio.start_background_task(face_recognition_worker, sio, stream_receiver)

        logging.info(f"ワーカープロセス {os.getpid()} の初期化が完了しました。")
        worker_initialized = True


# --- ルートとSocket.IOイベントハンドラ ---
@app.route("/")
def index():
    """クライアントに表示するHTMLをレンダリングする"""
    setup_worker_resources()
    # config.STREAM_URL はモードに応じて自動的に正しいURLが設定されている
    return render_template("index.html", stream_url=config.STREAM_URL)


# ★★★ 開発モードでのみ有効な映像ストリーミング用ルート ★★★
if config.IS_DEVELOPMENT_MODE:

    @app.route("/video_feed")
    def video_feed():
        """開発用カメラの映像をストリーミングする"""
        return Response(
            generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
        )


@sio.on("connect", namespace="/live")
def on_connect():
    """最初のクライアント接続時にワーカーの初期化をトリガー"""
    setup_worker_resources()
    logging.info("クライアントが接続しました。")
