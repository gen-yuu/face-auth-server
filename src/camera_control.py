# src/camera_control.py

import logging
import sys

import requests

from src.config import config

logger = logging.getLogger(__name__)


def init_raspi_camera():
    """Raspberry Piのカメラを初期化するAPIを呼び出す"""
    url = f"{config.RASPI_API_BASE_URL}/camera/init"
    params = {"width": config.RASPI_CAMERA_WIDTH, "height": config.RASPI_CAMERA_HEIGHT}
    try:
        logger.info(
            f"Raspberry Piカメラの初期化を試みます... URL: {url}, Params: {params}"
        )
        response = requests.post(url, params=params, timeout=10)
        response.raise_for_status()  # 2xx以外のステータスコードで例外を発生させる
        logger.info(f"Raspberry Piカメラの初期化に成功しました: {response.text}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Raspberry Piカメラの初期化に失敗しました: {e}")
        logger.error(
            "Raspberry Pi側のサーバーが起動しているか、URLが正しいか確認してください。"
        )
        sys.exit(1)  # 致命的なエラーとしてプログラムを終了


def release_raspi_camera():
    """Raspberry Piのカメラを解放するAPIを呼び出す"""
    url = f"{config.RASPI_API_BASE_URL}/camera/release"
    try:
        logger.info(f"Raspberry Piカメラの解放を試みます... URL: {url}")
        response = requests.post(url, timeout=10)
        response.raise_for_status()
        logger.info(f"Raspberry Piカメラの解放に成功しました: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Raspberry Piカメラの解放中にエラーが発生しました: {e}")
