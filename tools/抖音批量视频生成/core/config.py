"""
config.py - 配置管理模块
───────────────────────
管理应用的全局配置，支持 JSON 文件持久化。
"""

import json
import os
import sys
from pathlib import Path


# 图片生成尺寸配置（保留供扩展使用）
IMAGE_SIZE_MAP = {
    "1024x1024": (1024, 1024),
    "2048x2048": (2048, 2048),
    "2304x1728": (2304, 1728),
    "2496x1664": (2496, 1664),
    "2560x1440": (2560, 1440),
    "3024x1296": (3024, 1296),
    "4096x4096": (4096, 4096),
    "4694x3520": (4694, 3520),
    "4992x3328": (4992, 3328),
    "5404x3040": (5404, 3040),
    "6198x2656": (6198, 2656),
}

IMAGE_SIZE_LABELS = {
    "1024x1024": "1:1 (1024×1024) [1K]",
    "2048x2048": "1:1 (2048×2048) [2K]",
    "2304x1728": "4:3 (2304×1728) [2K]",
    "2496x1664": "3:2 (2496×1664) [2K]",
    "2560x1440": "16:9 (2560×1440) [2K]",
    "3024x1296": "21:9 (3024×1296) [2K]",
    "4096x4096": "1:1 (4096×4096) [4K]",
    "4694x3520": "4:3 (4694×3520) [4K]",
    "4992x3328": "3:2 (4992×3328) [4K]",
    "5404x3040": "16:9 (5404×3040) [4K]",
    "6198x2656": "21:9 (6198×2656) [4K]",
}


def get_app_dir() -> Path:
    """
    获取应用程序根目录（打包和开发模式兼容）。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_resource_dir() -> Path:
    """
    获取只读资源目录（config、ffmpeg 等打包进来的文件）。
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


class ConfigManager:
    """配置管理器（单例）"""

    _instance = None
    _default_config = {
        # TTS 配置（火山引擎）
        "volcengine_app_id": "",
        "volcengine_token": "",
        "volcengine_resource_id": "seed-tts-2.0",
        "tts_voice": "zh_female_zhimeng_uranus_bigtts",
        "tts_speed": 1.0,
        "tts_timeout": 30,
        # 视频输出
        "output_resolution": "1080x1920",
        "output_fps": 30,
        "bgm_volume": 30,
        "output_dir": "./output/",
        "ffmpeg_path": "./ffmpeg/ffmpeg.exe",
        # 字幕
        "subtitle_font": "Microsoft YaHei",
        "subtitle_font_size": 52,
        "subtitle_position": "bottom",
        "subtitle_position_y": 80,
        "subtitle_color": "&H00FFFFFF",
        "subtitle_outline": True,
        "subtitle_outline_color": "&H00000000",
        "subtitle_outline_size": 2,
        "subtitle_shadow": True,
        "subtitle_shadow_color": "&H80000000",
        "subtitle_shadow_offset": 2,
        "subtitle_remove_punctuation": False,
        "subtitle_max_chars": 0,
        "subtitle_offset_sec": 0.15,
        # 文本分段
        "text_segment_min_duration": 1.8,
        # 视频转场
        "transition_type": "none",
        "random_video_start": True,
        # AI 分段（豆包大模型）
        "doubao_api_key": "",
        "doubao_model": "ark-code-latest",
        "doubao_base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        # 封面
        "cover_bg_path": "",
        "cover_font_size": 80,
        # 路径记忆
        "default_material_folder": "",
        "default_bgm_folder": "",
        "to_publish_dir": "./to_publish/",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config_path = get_app_dir() / "config" / "settings.json"
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                for key, value in self._default_config.items():
                    if key not in self.config:
                        self.config[key] = value
            except Exception as e:
                print(f"配置文件加载失败，使用默认配置: {e}")
                self.config = self._default_config.copy()
        else:
            self.config = self._default_config.copy()
            self._save_config()

    def _save_config(self):
        """保存配置到文件"""
        os.makedirs(self._config_path.parent, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)

    def set(self, key, value):
        """设置配置项并保存"""
        self.config[key] = value
        self._save_config()

    def is_api_configured(self):
        """检查 API 配置是否完整"""
        return all(
            [
                self.get("volcengine_app_id"),
                self.get("volcengine_token"),
            ]
        )

    def get_image_size_px(self) -> tuple:
        """获取图片生成尺寸（像素）"""
        size_str = self.get("image_size", "2304x1728")
        return IMAGE_SIZE_MAP.get(size_str, (2304, 1728))


# 全局配置实例
config = ConfigManager()
