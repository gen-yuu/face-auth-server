import os
from pathlib import Path

from dotenv import load_dotenv

# プロジェクトのルートディレクトリを基準に.envを探す
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path=dotenv_path)


class Config:
    """
    アプリケーションの設定を管理するクラス
    環境変数から値を読み込む
    """

    # プロジェクトルート
    PROJECT_ROOT = project_root

    # サーバー設定
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # ストリーム設定
    RASPI_API_BASE_URL = os.getenv("RASPI_API_BASE_URL")
    RASPI_STREAM_URL = os.getenv("RASPI_STREAM_URL")
    if not RASPI_API_BASE_URL or not RASPI_STREAM_URL:
        raise ValueError(
            "環境変数 `RASPI_API_BASE_URL` と `RASPI_STREAM_URL` の両方を設定してください。"
        )

    # カメラ初期化設定
    RASPI_CAMERA_WIDTH = int(os.getenv("RASPI_CAMERA_WIDTH", 640))
    RASPI_CAMERA_HEIGHT = int(os.getenv("RASPI_CAMERA_HEIGHT", 480))

    # 顔認識設定
    FACE_DATA_DIR = PROJECT_ROOT / os.getenv("FACE_DATA_DIR", "data/people")
    RECOGNITION_MODEL = os.getenv("RECOGNITION_MODEL", "hog")
    WORKER_SLEEP_INTERVAL = float(os.getenv("WORKER_SLEEP_INTERVAL", 0.1))
    FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", 0.5))


# 設定クラスのインスタンスを作成
config = Config()
