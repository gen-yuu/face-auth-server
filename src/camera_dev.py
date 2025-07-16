# src/camera_dev.py

import atexit
import logging

import cv2

logger = logging.getLogger(__name__)

# プロセス内で単一のカメラインスタンスを保持
camera = None


def initialize_dev_camera():
    """ローカルの開発用カメラを初期化する"""
    global camera
    if camera is None or not camera.isOpened():
        logger.info("開発用カメラの初期化を試みます...")
        # 0は内蔵カメラ、1以上は外部カメラなど環境によって変わる
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            logger.error("開発用カメラを開けませんでした。")
            raise IOError("Cannot open webcam")
        logger.info("開発用カメラの初期化に成功しました。")
        # プロセス終了時にカメラを解放するよう登録
        atexit.register(release_dev_camera)


def release_dev_camera():
    """ローカルの開発用カメラを解放する"""
    global camera
    if camera and camera.isOpened():
        logger.info("開発用カメラを解放します。")
        camera.release()
        camera = None


def generate_frames():
    """カメラからフレームを読み込み、JPEG形式でエンコードしてyieldするジェネレータ"""
    global camera
    if camera is None or not camera.isOpened():
        logger.error("カメラが初期化されていません。")
        return

    while True:
        success, frame = camera.read()
        if not success:
            logger.warning("カメラからのフレーム取得に失敗しました。")
            break
        else:
            # フレームをJPEG形式にエンコード
            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            # multipart/x-mixed-replace 形式でフレームを返す
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
