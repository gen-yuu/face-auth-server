from __future__ import annotations

import logging
import pickle
from pathlib import Path

import face_recognition
import numpy as np

from src.config import config

logger = logging.getLogger(__name__)

# キャッシュファイルのパスをデータディレクトリ内に設定
CACHE_FILE = config.FACE_DATA_DIR / "_encodings.pkl"


class FaceDB:
    def __init__(self) -> None:
        self.embeddings = {}
        self.load()

    # --- Public API ---
    def reload(self) -> None:
        """キャッシュを削除し、顔データベースを再構築する"""
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        self.load()

    def match(self, enc: np.ndarray) -> str | None:
        """
        与えられた顔エンコーディングに最も一致する人物名を返す
        しきい値以下のマッチが見つからない場合はNoneを返す
        """
        best_id, best_dist = None, 1.0
        for uid, vecs in self.embeddings.items():
            # 1対多の距離計算
            distances = face_recognition.face_distance(vecs, enc)
            # 最も小さい距離を取得
            d = distances.min()
            if d < best_dist:
                best_id, best_dist = uid, d

        return best_id if best_dist < config.FACE_MATCH_THRESHOLD else None

    # --- Internal API---
    def load(self) -> None:
        """キャッシュから顔データベースを読み込む。なければ構築する。"""
        if CACHE_FILE.exists():
            try:
                self.embeddings = pickle.loads(CACHE_FILE.read_bytes())
                logger.info(
                    f"FaceDBキャッシュをロードしました ({len(self.embeddings)} 人分)"
                )
                return
            except Exception as e:
                logger.error(
                    f"FaceDBキャッシュの読み込みに失敗しました: {e}。再構築します。"
                )

        logger.info("FaceDBを構築しています...")
        if not config.FACE_DATA_DIR.exists():
            logger.warning(
                f"顔データディレクトリが見つかりません: {config.FACE_DATA_DIR}"
            )
            config.FACE_DATA_DIR.mkdir(parents=True, exist_ok=True)

        for user_dir in config.FACE_DATA_DIR.iterdir():
            if not user_dir.is_dir():
                continue

            encodings = []
            for img_path in user_dir.glob("*.*"):
                if not img_path.name.lower().endswith((".png", ".jpg", ".jpeg")):
                    continue

                try:
                    img = face_recognition.load_image_file(img_path)
                    locs = face_recognition.face_locations(
                        img, model="hog"
                    )  # hogで高速化

                    if len(locs) != 1:
                        logger.warning(
                            f"画像 '{img_path.relative_to(config.PROJECT_ROOT)}' には顔が{len(locs)}個検出されたため、スキップします。"
                        )
                        continue

                    enc = face_recognition.face_encodings(img, locs)[0]
                    encodings.append(enc)
                    logger.info(
                        f"エンコード完了: {img_path.relative_to(config.PROJECT_ROOT)}"
                    )

                except Exception as e:
                    logger.error(f"画像 '{img_path.name}' の処理中にエラー: {e}")

            if encodings:
                self.embeddings[user_dir.name] = np.vstack(encodings)

        try:
            CACHE_FILE.write_bytes(pickle.dumps(self.embeddings))
            logger.info(
                f"FaceDBを構築し、キャッシュを保存しました ({len(self.embeddings)} 人分)"
            )
        except Exception as e:
            logger.error(f"FaceDBキャッシュの保存に失敗しました: {e}")
