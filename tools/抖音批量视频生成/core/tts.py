"""
tts.py - TTS 语音合成模块
────────────────────────
通过火山引擎 WebSocket 协议进行文字转语音（TTS），
返回合成的音频文件路径和字级时间戳。
"""

import os
import json
import uuid
import struct
import time
import gzip
import asyncio
from pathlib import Path
from .config import config


def get_app_dir() -> Path:
    """获取应用程序根目录"""
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def _strip_llm_wrapper(text: str) -> str:
    """剥离 LLM 偶尔返回的 JSON 包裹"""
    import re as _re

    t = text.strip()
    t = _re.sub(r"^```(?:json)?\s*", "", t, flags=_re.IGNORECASE)
    t = _re.sub(r"\s*```$", "", t).strip()
    if t.startswith("{"):
        try:
            obj = json.loads(t)
            for key in ("rewritten", "content", "text", "result", "output"):
                if key in obj and isinstance(obj[key], str):
                    return obj[key].strip()
        except Exception:
            pass
    return t


def _clean_text_for_tts(text: str) -> str:
    """
    清理文案供 TTS 使用：删除空白行、多余换行和空格。
    """
    import re as _re

    text = _strip_llm_wrapper(text)
    lines = text.split("\n")
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    text = "\n".join(cleaned_lines)
    text = text.replace("\n", " ")
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


# ── TTS 字数统计 ──────────────────────────────────────────


class TTSStats:
    """记录本次运行和历史累计的 TTS 提交字数"""

    def __init__(self):
        self._path = get_app_dir() / "tts_stats.json"
        self._session = 0
        self._total = self._load_total()

    def _load_total(self) -> int:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return int(data.get("total", 0))
        except Exception:
            return 0

    def add(self, char_count: int):
        self._session += char_count
        self._total += char_count
        try:
            self._path.write_text(
                json.dumps({"total": self._total}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def reset_session(self):
        self._session = 0

    @property
    def session(self) -> int:
        return self._session

    @property
    def total(self) -> int:
        return self._total


tts_stats = TTSStats()


# ── 依赖导入 ────────────────────────────────────────────────
websockets = None
AudioSegment = None


def _import_dependencies():
    """延迟导入依赖"""
    global websockets, AudioSegment
    if websockets is None:
        try:
            import websockets as _websockets
            import websockets.legacy.client  # noqa: F401

            websockets = _websockets
        except ImportError:
            raise ImportError(
                "websockets 未安装，请运行: pip install websockets"
            )
    if AudioSegment is None:
        try:
            from pydub import AudioSegment as _AudioSegment

            AudioSegment = _AudioSegment
        except Exception:
            pass


# ── 异常类 ────────────────────────────────────────────────


class TTSAuthError(Exception):
    """鉴权失败：AppID 或 Access Token 错误"""


class TTSNetworkError(Exception):
    """网络连接失败或超时"""


class TTSParamError(Exception):
    """请求参数错误：如音色 ID 不存在"""


# ── 协议常量 ──────────────────────────────────────────────

PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001

MSG_FULL_CLIENT = 0b0001
MSG_FULL_SERVER = 0b1001
MSG_AUDIO_ONLY_RESP = 0b1011
MSG_ERROR = 0b1111

FLAG_WITH_EVENT = 0b0100
SERIAL_JSON = 0b0001
SERIAL_RAW = 0b0000
COMPRESS_NONE = 0b0000

EVENT_START_CONN = 1
EVENT_FINISH_CONN = 2
EVENT_CONN_STARTED = 50
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_SESSION_START = 150
EVENT_SESSION_DONE = 152
EVENT_SESSION_FAIL = 153
EVENT_TASK_REQUEST = 200

WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"


# ── 帧编码工具 ────────────────────────────────────────────


def _make_header(msg_type, flags, serial, compress):
    b0 = (PROTOCOL_VERSION << 4) | HEADER_SIZE
    b1 = (msg_type << 4) | flags
    b2 = (serial << 4) | compress
    return bytes([b0, b1, b2, 0x00])


def _conn_frame(event, payload_bytes=b"{}"):
    """连接级帧（StartConnection / FinishConnection）"""
    header = _make_header(MSG_FULL_CLIENT, FLAG_WITH_EVENT, SERIAL_JSON, COMPRESS_NONE)
    return (
        header
        + struct.pack(">i", event)
        + struct.pack(">I", len(payload_bytes))
        + payload_bytes
    )


def _session_frame(event, sid_bytes, payload_bytes=b"{}"):
    """会话级帧（StartSession / FinishSession / TaskRequest）"""
    header = _make_header(MSG_FULL_CLIENT, FLAG_WITH_EVENT, SERIAL_JSON, COMPRESS_NONE)
    return (
        header
        + struct.pack(">i", event)
        + struct.pack(">I", len(sid_bytes))
        + sid_bytes
        + struct.pack(">I", len(payload_bytes))
        + payload_bytes
    )


def _decode_frame(data: bytes):
    """解析服务端下行帧"""
    if len(data) < 4:
        return MSG_ERROR, None, b"frame too short", False

    b1 = data[1]
    b2 = data[2]
    msg_type = (b1 >> 4) & 0xF
    flags = b1 & 0xF
    compress = b2 & 0xF

    pos = 4
    event = None

    if flags & 0x4:
        if len(data) < pos + 4:
            return msg_type, None, b"", False
        event = struct.unpack(">i", data[pos : pos + 4])[0]
        pos += 4

    if msg_type == MSG_ERROR:
        pos += 4
        return msg_type, event, data[pos:], False

    segments = []
    while pos + 4 <= len(data):
        seg_size = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        end = pos + seg_size
        segments.append(data[pos : min(end, len(data))])
        pos = end

    payload = segments[-1] if segments else b""

    if compress == COMPRESS_NONE and payload:
        pass
    elif payload:
        try:
            payload = gzip.decompress(payload)
        except Exception:
            pass

    return msg_type, event, payload, False


# ── 主类 ──────────────────────────────────────────────────


class TTSGenerator:
    """火山引擎 TTS 语音合成器"""

    def __init__(self):
        self.app_id = config.get("volcengine_app_id")
        self.token = config.get("volcengine_token")
        self.resource_id = config.get("volcengine_resource_id", "")
        self.timeout = config.get("tts_timeout", 30)
        self.temp_dir = get_app_dir() / "temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        self.output_path = None
        self.timestamp_path = None

    def _reload_config(self):
        """每次生成前重新读取最新配置"""
        self.app_id = config.get("volcengine_app_id", "")
        self.token = config.get("volcengine_token", "")
        self.resource_id = config.get("volcengine_resource_id", "")

    def generate(
        self,
        text,
        speed=None,
        voice=None,
        volume=100,
        progress_callback=None,
    ):
        """
        生成语音。

        :param text:              口播文案
        :param speed:             语速倍数 0.8~1.5
        :param voice:             音色 speaker ID
        :param volume:            音量百分比 50~200
        :param progress_callback: 可选回调 callback(percent: int, message: str)
        :return: (audio_path: str, timestamps: list)
        """
        _import_dependencies()
        self._reload_config()

        text = _clean_text_for_tts(text)
        if not text:
            raise ValueError("文案内容为空，无法合成语音")

        if not self.app_id:
            raise TTSAuthError("请在「设置」中填写火山引擎 AppID")
        if not self.token:
            raise TTSAuthError("请在「设置」中填写火山引擎 Access Token")
        if not self.resource_id:
            raise TTSParamError("请在「设置」中填写资源 ID（如 seed-tts-2.0）")

        unique_id = uuid.uuid4().hex[:8]
        self.output_path = self.temp_dir / f"tts_output_{unique_id}.mp3"
        self.timestamp_path = self.temp_dir / f"tts_timestamps_{unique_id}.json"

        tts_stats.add(len(text))

        if speed is None:
            speed = config.get("tts_speed", 1.0)
        if voice is None:
            voice = config.get("tts_voice", "zh_female_zhizhi_mars_bigtts")

        speech_rate = int((speed - 1.0) * 100)
        speech_rate = max(-50, min(100, speech_rate))

        def _report(percent, message):
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except Exception:
                    pass

        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                _report(0, "正在连接语音合成服务...")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    audio_bytes, raw_timestamps = loop.run_until_complete(
                        asyncio.wait_for(
                            self._ws_generate(
                                text, voice, speech_rate, volume, _report
                            ),
                            timeout=self.timeout,
                        )
                    )
                finally:
                    loop.close()

                _report(90, "音频接收完成，正在保存...")

                with open(self.output_path, "wb") as f:
                    f.write(audio_bytes)

                timestamps = self._normalize_timestamps(raw_timestamps)
                with open(self.timestamp_path, "w", encoding="utf-8") as f:
                    json.dump(timestamps, f, ensure_ascii=False, indent=2)

                _report(100, "生成完成")
                return str(self.output_path), timestamps

            except (TTSAuthError, TTSParamError):
                raise

            except asyncio.TimeoutError:
                last_error = TTSNetworkError(
                    f"TTS请求超时（超过{self.timeout}秒），请检查网络连接后重试"
                )
            except (ConnectionRefusedError, OSError) as e:
                last_error = TTSNetworkError(
                    f"无法连接到语音合成服务，请检查网络（{e}）"
                )
            except TTSNetworkError as e:
                last_error = e
            except Exception as e:
                last_error = Exception(f"TTS生成失败: {e}")

            if attempt < max_retries:
                time.sleep(1)

        raise last_error

    def get_audio_duration(self, audio_path=None):
        """直接用 ffprobe 获取音频时长"""
        import subprocess

        if audio_path is None:
            audio_path = self.output_path

        ffmpeg_dir = get_app_dir() / "ffmpeg"
        ffprobe_path = ffmpeg_dir / "ffprobe.exe"
        if not ffprobe_path.exists():
            ffprobe_path = "ffprobe"

        try:
            result = subprocess.run(
                [
                    str(ffprobe_path),
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
            )
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception:
            if hasattr(self, "timestamp_path") and Path(self.timestamp_path).exists():
                try:
                    ts = json.loads(
                        Path(self.timestamp_path).read_text(encoding="utf-8")
                    )
                    if ts:
                        return ts[-1].get("end_time", 0.0)
                except Exception:
                    pass
            try:
                _import_dependencies()
                audio = AudioSegment.from_file(audio_path)
                return len(audio) / 1000.0
            except Exception:
                return 0.0

    # ── WebSocket 核心 ─────────────────────────────────────

    async def _ws_generate(self, text, voice, speech_rate, volume, report):
        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        audio_chunks = []
        timestamps = []

        session_id = str(uuid.uuid4()).replace("-", "")
        sid_bytes = session_id.encode()

        try:
            async with websockets.connect(WS_URL, additional_headers=headers) as ws:
                # 1. StartConnection
                await ws.send(_conn_frame(EVENT_START_CONN))
                await self._expect_event(ws, EVENT_CONN_STARTED, "建连失败")
                report(20, "连接成功，正在初始化...")

                # 2. StartSession
                session_meta = json.dumps(
                    {
                        "user": {"uid": "video_tool_user"},
                        "event": EVENT_START_SESSION,
                        "req_params": {
                            "speaker": voice,
                            "audio_params": {
                                "format": "mp3",
                                "sample_rate": 24000,
                                "bit_rate": 128000,
                                "speech_rate": speech_rate,
                                "volume": volume,
                                "enable_subtitle": True,
                            },
                        },
                    },
                    ensure_ascii=False,
                ).encode()

                await ws.send(
                    _session_frame(EVENT_START_SESSION, sid_bytes, session_meta)
                )
                await self._expect_event(ws, EVENT_SESSION_START, "Session 启动失败")
                report(40, "正在合成语音，请稍候...")

                # 3. TaskRequest
                task_payload = json.dumps(
                    {
                        "event": EVENT_TASK_REQUEST,
                        "req_params": {"text": text},
                    },
                    ensure_ascii=False,
                ).encode()
                await ws.send(
                    _session_frame(EVENT_TASK_REQUEST, sid_bytes, task_payload)
                )

                # 4. FinishSession
                await ws.send(_session_frame(EVENT_FINISH_SESSION, sid_bytes))

                # 5. 接收音频 + 时间戳
                report(60, "语音合成中，接收音频数据...")
                async for raw in ws:
                    if isinstance(raw, str):
                        continue

                    msg_type, event, payload, _ = _decode_frame(raw)

                    if msg_type == MSG_AUDIO_ONLY_RESP:
                        if payload:
                            audio_chunks.append(payload)

                    elif msg_type == MSG_FULL_SERVER:
                        if payload:
                            try:
                                info = json.loads(payload)
                                words = info.get("words", [])
                                if words:
                                    timestamps.extend(words)
                            except Exception:
                                pass
                        if event == EVENT_SESSION_DONE:
                            break
                        if event == EVENT_SESSION_FAIL:
                            err_msg = (
                                payload.decode(errors="replace") if payload else ""
                            )
                            if "speaker" in err_msg.lower():
                                raise TTSParamError(
                                    "音色ID不存在，请检查设置中的音色配置"
                                )
                            raise Exception(f"Session 失败: {err_msg}")

                    elif msg_type == MSG_ERROR:
                        err_msg = payload.decode(errors="replace") if payload else ""
                        raise Exception(f"服务端错误: {err_msg}")

                # 6. FinishConnection
                await ws.send(_conn_frame(EVENT_FINISH_CONN))

        except websockets.exceptions.InvalidStatus as e:
            code = e.response.status_code if hasattr(e, "response") else 0
            if code in (401, 403):
                raise TTSAuthError(
                    "AppID 或 Access Token 错误，请在设置中重新填写"
                )
            raise TTSNetworkError(f"WebSocket 握手失败（HTTP {code}）")

        except websockets.exceptions.WebSocketException as e:
            raise TTSNetworkError(f"WebSocket 连接异常: {e}")

        return b"".join(audio_chunks), timestamps

    # ── 工具方法 ──────────────────────────────────────────

    @staticmethod
    async def _expect_event(ws, expected_event, err_msg):
        """等待一帧并校验 event 类型"""
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        if isinstance(raw, str):
            raise Exception(f"{err_msg}: {raw}")
        msg_type, event, payload, _ = _decode_frame(raw)
        if msg_type == MSG_ERROR or event != expected_event:
            detail = payload.decode(errors="replace") if payload else ""
            raise Exception(
                f"{err_msg}（收到 event={event}，期望={expected_event}）: {detail}"
            )

    @staticmethod
    def _normalize_timestamps(raw_words: list) -> list:
        """统一时间戳字段名为下划线格式"""
        return [
            {
                "word": w.get("word", ""),
                "start_time": w.get("startTime", w.get("start_time", 0.0)),
                "end_time": w.get("endTime", w.get("end_time", 0.0)),
                "confidence": w.get("confidence", 1.0),
            }
            for w in raw_words
        ]
