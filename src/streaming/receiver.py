# src/streaming/receiver.py

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class StreamReceiver:
    """
    バックグラウンドスレッドでMJPEGストリームを受信し、最新フレームを管理するクラス
    """

    def __init__(self, stream_url: str):
        self._stream_url = stream_url
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self.connected_event = threading.Event()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("StreamReceiverスレッドを開始しました。")

    def _capture_loop(self):
        """ストリームから継続的にフレームをキャプチャするループ"""
        while True:
            try:
                cap = cv2.VideoCapture(self._stream_url, cv2.CAP_FFMPEG)
                if not cap.isOpened():
                    logger.error(
                        f"ストリームを開けません: {self._stream_url}。5秒後に再試行します..."
                    )
                    self.connected_event.clear()
                    time.sleep(5)
                    continue

                logger.info(f"ストリームに接続成功: {self._stream_url}")
                self.connected_event.set()

                while True:
                    success, frame = cap.read()
                    if not success:
                        logger.warning(
                            "ストリームの読み込みに失敗しました。再接続を試みます。"
                        )
                        self.connected_event.clear()
                        break

                    with self._lock:
                        self._frame = frame
                    # CPU負荷を少し下げるための短い待機
                    time.sleep(0.01)

            except Exception as e:
                logger.error(f"キャプチャループで例外発生: {e}。5秒後に再試行します...")
                self.connected_event.clear()
                time.sleep(5)

    def get_frame(self) -> Optional[np.ndarray]:
        """最新のフレームをスレッドセーフに取得する"""
        if not self.connected_event.is_set():
            return None
        with self._lock:
            return self._frame.copy() if self._frame is not None else None


# src/recognition/worker.py

import logging

import cv2
import face_recognition
from eventlet import tpool
from flask_socketio import SocketIO

from src.config import config
from src.recognition.face_db import FaceDB
from src.streaming.receiver import StreamReceiver

logger = logging.getLogger(__name__)


def process_frame_for_faces(frame_bgr: cv2.Mat, face_db: FaceDB):
    """
    1フレーム分の画像処理と顔認識を行う、CPU負荷の高い関数。
    この関数全体がtpoolで実行されることで、メインループのブロッキングを防ぐ。
    """
    if frame_bgr is None:
        return None

    # 1. 画像の前処理
    small_frame_rgb = cv2.cvtColor(
        cv2.resize(frame_bgr, (0, 0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB
    )

    # 2. 顔の位置特定とエンコード
    face_locations = face_recognition.face_locations(
        small_frame_rgb, model=config.RECOGNITION_MODEL
    )
    if not face_locations:
        return []  # 顔がなければ空のリストを返す

    face_encodings = face_recognition.face_encodings(small_frame_rgb, face_locations)

    # 3. 検出された顔のマッチング
    faces_data = []
    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):
        name = face_db.match(face_encoding) or "Unknown"
        faces_data.append(
            {
                "id": name,
                "x": int(left * 4),
                "y": int(top * 4),
                "w": int((right - left) * 4),
                "h": int((bottom - top) * 4),
            }
        )

    return faces_data


def face_recognition_worker(sio: SocketIO, stream_receiver: StreamReceiver):
    """
    顔認識ワーカー。フレームを取得し、重い処理をtpoolにオフロードする。
    """
    logger.info("顔認識ワーカーを起動しました。")

    # FaceDBの初期化を同期的に行う
    logger.info("FaceDBの準備を開始します...")
    face_db = FaceDB()
    logger.info("FaceDBの準備が完了しました。")

    logger.info("ストリームへの接続を待っています...")
    while not stream_receiver.connected_event.wait(timeout=5):
        logger.warning("まだストリームに接続できません...")
    logger.info("ストリーム接続完了。顔認識ループを開始します。")

    while True:
        # eventletのグリーンレットに制御を渡し、他のI/O処理を妨げない
        sio.sleep(config.WORKER_SLEEP_INTERVAL)

        try:
            # フレーム取得
            frame = stream_receiver.get_frame()
            if frame is None:
                continue

            # CPU負荷の高い処理をtpoolにオフロード
            faces_data = tpool.execute(process_frame_for_faces, frame, face_db)

            # ★★★ faces_dataがNoneでない限り、常にemitするよう修正 ★★★
            # faces_dataが空リストの場合、フロント側で枠がクリアされる
            if faces_data is not None:
                if faces_data:
                    recognized_names = [
                        face["id"] for face in faces_data if face["id"] != "Unknown"
                    ]
                    logger.info(
                        f"検出された顔数: {len(faces_data)} (認識: {', '.join(recognized_names) or 'なし'})"
                    )
                else:
                    logger.debug("顔は検出されませんでした。")

                sio.emit("faces_update", {"faces": faces_data}, namespace="/live")

        except Exception as e:
            logger.error(f"顔認識処理ループで予期せぬエラー: {e}", exc_info=True)
