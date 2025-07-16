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
