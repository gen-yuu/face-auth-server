# main.py
# このファイルはGunicornの起動エントリーポイントとして機能します。

import logging
import signal
import sys

# アプリケーションオブジェクトをインポート
from src.app import app

# クリーンアップ用の関数をインポート
from src.camera_control import release_raspi_camera


# --- シグナルハンドラによる正常なシャットダウン処理 ---
def graceful_shutdown(signum, frame):
    """
    SIGTERMやSIGINTを受け取ったときに、クリーンアップ処理を実行する
    """
    logging.info(
        f"シグナル {signal.Signals(signum).name} を受信。シャットダウンシーケンスを開始します..."
    )
    # このシャットダウン処理は、Gunicornのマスタープロセスで実行されます。
    release_raspi_camera()
    logging.info("アプリケーションを正常にシャットダウンしました。")
    sys.exit(0)


# Gunicornが送信するSIGTERMと、Ctrl+CによるSIGINTを捕捉
signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

# Gunicornからこの 'app' オブジェクトが参照されます。
if __name__ == "__main__":
    print("このスクリプトは直接実行できません。Gunicorn経由で起動してください。")
    print("例: gunicorn -c gunicorn.conf.py main:app")
