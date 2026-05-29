"""
task_queue.py - 任务队列数据模型
──────────────────────────────
定义视频合成任务的数据结构。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CompositionTask:
    """单个视频合成任务"""

    task_id: str
    name: str
    script_text: str
    audio_path: str
    segments: list  # 分段信息列表
    bgm_path: str
    bgm_volume: int
    output_count: int
    resolution: str = "1080x1920"
    fps: int = 30
    status: str = "pending"  # pending / running / done / failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    result_message: str = ""
    output_paths: list = field(default_factory=list)
    progress: float = 0.0
    timestamps: list = field(default_factory=list)


def generate_task_id() -> str:
    """生成唯一任务 ID"""
    return str(uuid.uuid4())[:8]
