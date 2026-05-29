"""
video_composer.py - 视频合成引擎
──────────────────────────────
负责将分段音频、随机素材、BGM、字幕合成为最终视频。
"""

import os
import random
import subprocess
import logging
import sys
from datetime import datetime
from pathlib import Path
from .config import config, get_app_dir

CREATE_NO_WINDOW = 0x08000000

SUBPROCESS_KWARGS = {}
if sys.platform == "win32":
    SUBPROCESS_KWARGS["creationflags"] = CREATE_NO_WINDOW
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    SUBPROCESS_KWARGS["startupinfo"] = startupinfo

SUBPROCESS_KWARGS["encoding"] = "utf-8"
SUBPROCESS_KWARGS["errors"] = "ignore"

AudioSegment = None
_pydub_configured = False

log_dir = get_app_dir() / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"video_composer_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)

logger = logging.getLogger("VideoComposer")


class VideoComposer:
    """视频合成引擎"""

    SUPPORTED_VIDEO_FORMATS = [
        ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"
    ]
    SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav", ".aac", ".flac"]

    def __init__(self):
        self.temp_dir = get_app_dir() / "temp"
        self.output_dir = Path(config.get("output_dir", "./output/"))
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.ffmpeg_path = self._get_ffmpeg_path()
        self.resolution = config.get("output_resolution", "1080x1920")
        self.fps = config.get("output_fps", 30)
        res_part = self.resolution.split(" ")[0]
        self.width, self.height = map(int, res_part.split("x"))
        logger.info("VideoComposer 初始化完成, 分辨率: %s, 帧率: %d", self.resolution, self.fps)

    def _configure_pydub(self):
        """安全地配置 pydub"""
        global AudioSegment, _pydub_configured
        if _pydub_configured:
            return
        try:
            ffmpeg_dir = get_app_dir() / "ffmpeg"
            ffmpeg_path = ffmpeg_dir / "ffmpeg.exe"
            ffprobe_path = ffmpeg_dir / "ffprobe.exe"

            if ffmpeg_path.exists():
                os.environ["PATH"] = (
                    str(ffmpeg_dir) + os.pathsep + os.environ.get("PATH", "")
                )
                os.environ["FFMPEG_BINARY"] = str(ffmpeg_path)
                os.environ["FFPROBE_BINARY"] = str(ffprobe_path)

            from pydub import AudioSegment as _AudioSegment

            AudioSegment = _AudioSegment
            _pydub_configured = True
            logger.info("pydub 配置完成")
        except Exception as e:
            logger.warning("pydub 配置失败: %s", e)

    def _get_ffmpeg_path(self):
        """获取 ffmpeg 路径"""
        from .config import get_resource_dir

        ffmpeg_exe = get_resource_dir() / "ffmpeg" / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)
        bin_ffmpeg = get_app_dir() / "bin" / "ffmpeg.exe"
        if bin_ffmpeg.exists():
            return str(bin_ffmpeg)
        return "ffmpeg"

    def _get_ffprobe_path(self):
        """获取 ffprobe 路径"""
        from .config import get_resource_dir

        ffprobe_exe = get_resource_dir() / "ffmpeg" / "ffprobe.exe"
        if ffprobe_exe.exists():
            return str(ffprobe_exe)
        bin_ffprobe = get_app_dir() / "bin" / "ffprobe.exe"
        if bin_ffprobe.exists():
            return str(bin_ffprobe)
        return "ffprobe"

    def _get_video_duration(self, video_path):
        """获取视频时长（秒）"""
        ffprobe_path = self._get_ffprobe_path()
        cmd = [
            ffprobe_path, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        try:
            output = result.stdout.strip()
            if not output:
                return self._get_video_duration_ffmpeg_fallback(video_path)
            return float(output)
        except Exception:
            return self._get_video_duration_ffmpeg_fallback(video_path)

    def _get_video_duration_ffmpeg_fallback(self, video_path):
        """使用 ffmpeg 作为 fallback 获取视频时长"""
        cmd = [self.ffmpeg_path, "-i", str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        try:
            import re
            match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", result.stderr)
            if match:
                h, m, s, cs = map(int, match.groups())
                return h * 3600 + m * 60 + s + cs / 100.0
        except Exception:
            pass
        return 0.0

    def _scan_video_folder(self, folder_path):
        """扫描文件夹下所有支持的视频文件"""
        logger.info("扫描素材文件夹: %s", folder_path)
        videos = []
        folder = Path(folder_path)
        if not folder.exists():
            logger.error("文件夹不存在: %s", folder_path)
            return videos
        for ext in self.SUPPORTED_VIDEO_FORMATS:
            videos.extend(list(folder.rglob(f"*{ext}")))
            videos.extend(list(folder.rglob(f"*{ext.upper()}")))
        video_list = [str(v) for v in videos]
        logger.info("  找到 %d 个视频文件", len(video_list))
        return video_list

    def _crop_single_clip(self, input_path, output_path, duration):
        """从单个素材裁出指定时长"""
        if duration <= 0:
            logger.warning("  裁剪时长异常: %ss，自动修正为1s", duration)
            duration = 1.0

        video_duration = self._get_video_duration(input_path)
        if video_duration <= 0:
            return False

        random_start = 0.0
        if config.get("random_video_start", True) and video_duration > duration * 1.5:
            max_start = video_duration - duration
            random_start = random.uniform(0, max_start * 0.8)

        cmd = [
            self.ffmpeg_path,
            "-ss", str(random_start),
            "-i", str(input_path),
            "-t", str(duration),
            "-vf", (
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:-1:-1:color=black"
            ),
            "-r", str(self.fps),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        return result.returncode == 0

    def _crop_video_segment(self, input_path, output_path, duration, all_videos=None):
        """裁剪视频片段（素材不足时自动拼接多个素材）"""
        logger.info("开始裁剪视频: %s, 目标时长: %.2fs", input_path, duration)
        video_duration = self._get_video_duration(input_path)
        if video_duration <= 0:
            return False

        if video_duration >= duration:
            return self._crop_single_clip(input_path, output_path, duration)

        # 素材不足：拼接更多素材
        if all_videos and len(all_videos) > 1:
            clip_paths = []
            remaining = duration
            last_used = input_path
            clip_idx = 0

            tmp = self.temp_dir / f"_mc_{id(output_path)}_{clip_idx}.mp4"
            clip_idx += 1
            ok = self._crop_single_clip(last_used, tmp, min(video_duration * 0.95, remaining))
            if not ok:
                all_videos = None
            else:
                clip_paths.append(str(tmp))
                remaining -= self._get_video_duration(str(tmp))

            while remaining > 0.1 and all_videos:
                candidates = [v for v in all_videos if v != last_used]
                if not candidates:
                    candidates = all_videos
                next_video = random.choice(candidates)
                next_dur = self._get_video_duration(next_video)
                if next_dur <= 0:
                    break
                take = min(next_dur * 0.95, remaining)
                tmp = self.temp_dir / f"_mc_{id(output_path)}_{clip_idx}.mp4"
                clip_idx += 1
                ok = self._crop_single_clip(next_video, tmp, take)
                if ok:
                    clip_paths.append(str(tmp))
                    remaining -= self._get_video_duration(str(tmp))
                    last_used = next_video
                else:
                    break

            if clip_paths:
                if len(clip_paths) == 1:
                    import shutil
                    shutil.move(clip_paths[0], output_path)
                else:
                    ok = self._concat_videos(clip_paths, output_path)
                    for p in clip_paths:
                        try:
                            Path(p).unlink()
                        except Exception:
                            pass
                    if not ok:
                        all_videos = None
                    else:
                        return True

        # 兜底：循环播放
        cmd = [
            self.ffmpeg_path, "-stream_loop", "-1",
            "-i", str(input_path), "-t", str(duration),
            "-vf", (
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:-1:-1:color=black"
            ),
            "-r", str(self.fps),
            "-c:v", "libx264", "-c:a", "aac", "-y",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        if result.returncode != 0:
            logger.error("FFmpeg 循环失败: %s", result.stderr)
            return False
        return True

    def _concat_videos(self, video_list, output_path):
        """拼接多个视频文件"""
        list_path = self.temp_dir / "filelist.txt"
        with open(list_path, "w", encoding="utf-8") as f:
            for video in video_list:
                f.write(f"file '{os.path.abspath(video)}'\n")

        cmd = [
            self.ffmpeg_path, "-f", "concat", "-safe", "0",
            "-i", str(list_path),
            "-c:v", "libx264", "-c:a", "aac",
            "-r", str(self.fps), "-y",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        os.remove(list_path)
        if result.returncode != 0:
            logger.error("视频拼接失败: %s", result.stderr)
            return False
        return True

    def _concat_videos_with_transition(self, video_list, output_path, transition_duration=0.3):
        """使用 xfade 转场拼接多个视频"""
        if len(video_list) == 1:
            import shutil
            shutil.copy(video_list[0], output_path)
            return True

        inputs = []
        for v in video_list:
            inputs += ["-i", str(v)]

        durations = [self._get_video_duration(v) for v in video_list]
        filter_parts = []
        current_offset = 0.0
        last_label = "[0:v]"
        for i in range(1, len(video_list)):
            current_offset += durations[i - 1] - transition_duration
            out_label = f"[v{i}]"
            filter_parts.append(
                f"{last_label}[{i}:v]xfade=transition=fade:"
                f"duration={transition_duration}:offset={current_offset}{out_label}"
            )
            last_label = out_label

        filter_complex = ";".join(filter_parts)
        cmd = [
            self.ffmpeg_path, *inputs,
            "-filter_complex", filter_complex,
            "-map", last_label,
            "-c:v", "libx264", "-r", str(self.fps), "-y",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        if result.returncode != 0:
            logger.error("转场拼接失败: %s", result.stderr)
            return False
        return True

    def _mix_audio(self, tts_path, bgm_path, bgm_volume, output_path, total_duration):
        """混合口播音频和 BGM"""
        try:
            if not bgm_path or not Path(bgm_path).exists():
                cmd = [
                    self.ffmpeg_path, "-i", str(tts_path),
                    "-t", str(total_duration), "-c:a", "libmp3lame",
                    "-ar", "44100",
                    "-filter:a", (
                        "aformat=sample_rates=44100:sample_fmts=fltp:channel_layouts=stereo,"
                        "apad=pad_dur=1,loudnorm=I=-23:LRA=11:TP=-2"
                    ),
                    "-y", str(output_path),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
                return result.returncode == 0

            if bgm_path and Path(bgm_path).exists():
                import shutil
                local_bgm = self.temp_dir / "bgm_tmp.mp3"
                try:
                    shutil.copy2(bgm_path, local_bgm)
                    bgm_vol = bgm_volume / 100.0
                    pad_dur = total_duration + 1.0
                    filter_complex = (
                        f"[0:a]aformat=sample_rates=44100:sample_fmts=fltp:channel_layouts=stereo,"
                        f"atrim=duration={total_duration},apad=pad_dur=1[tts];"
                        f"[1:a]aformat=sample_rates=44100:sample_fmts=fltp:channel_layouts=stereo,"
                        f"volume={bgm_vol},aloop=loop=-1:size=2147483647,atrim=duration={pad_dur}[bgm];"
                        f"[tts][bgm]amix=inputs=2:duration=first:weights=2 1[aout];"
                        f"[aout]loudnorm=I=-23:LRA=11:TP=-2[aout]"
                    )
                    cmd = [
                        self.ffmpeg_path,
                        "-i", str(tts_path), "-i", str(local_bgm),
                        "-filter_complex", filter_complex,
                        "-map", "[aout]", "-c:a", "libmp3lame",
                        "-ar", "44100", "-t", str(total_duration),
                        "-y", str(output_path),
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
                    if local_bgm.exists():
                        local_bgm.unlink()
                    return result.returncode == 0
                except Exception as e:
                    logger.warning("复制BGM到临时目录失败: %s", e)
                    if "local_bgm" in locals() and local_bgm.exists():
                        local_bgm.unlink()

            import shutil
            shutil.copy2(str(tts_path), str(output_path))
            return True
        except Exception as e:
            logger.error("音频混合最终失败: %s", e, exc_info=True)
            return False

    def _burn_subtitle(self, video_path, subtitle_path, output_path):
        """烧录字幕到视频"""
        import shutil

        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        local_ass = output_dir / "subtitle_tmp.ass"

        try:
            shutil.copy2(subtitle_path, local_ass)
            output_filename = Path(output_path).name

            cmd = [
                self.ffmpeg_path,
                "-i", str(video_path),
                "-vf", "subtitles=subtitle_tmp.ass",
                "-c:v", "libx264", "-c:a", "copy",
                "-y", output_filename,
            ]
            result = subprocess.run(
                cmd, cwd=str(output_dir),
                capture_output=True, text=True, **SUBPROCESS_KWARGS,
            )
            if result.returncode != 0:
                logger.error("字幕烧录失败: %s", result.stderr)
                return False
            return True
        finally:
            if local_ass.exists():
                try:
                    local_ass.unlink()
                except Exception:
                    pass

    def _pad_video_end(self, video_path, output_path, extra_seconds):
        """通过复制最后一帧延长视频结尾"""
        extra_frames = int(extra_seconds * self.fps) + 2
        cmd = [
            self.ffmpeg_path, "-i", str(video_path),
            "-vf", f"tpad=stop={extra_frames}:stop_mode=clone",
            "-c:v", "libx264", "-r", str(self.fps), "-y",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        if result.returncode != 0:
            logger.error("tpad 失败: %s", result.stderr)
            return False
        return True

    def prepend_cover_image(
        self, video_path: str, title: str, output_path: str,
        cover_bg_path: str = None, cover_duration: float = 0.3,
    ) -> bool:
        """生成封面帧并拼接到视频开头"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.error("Pillow 未安装，无法生成封面")
            return False

        cover_img_path = Path(self.temp_dir) / "cover_with_title.png"
        cover_clip = Path(self.temp_dir) / "cover_clip.mp4"

        try:
            if cover_bg_path and Path(cover_bg_path).exists():
                bg = Image.open(cover_bg_path).convert("RGB")
                bg = bg.resize((self.width, self.height), Image.LANCZOS)
            else:
                bg = Image.new("RGB", (self.width, self.height), (0, 0, 0))

            draw = ImageDraw.Draw(bg)
            font_size = 180

            font_candidates = [
                r"C:\Windows\Fonts\STLITI.TTF",
                r"C:\Windows\Fonts\msyhbd.ttc",
                r"C:\Windows\Fonts\msyh.ttc",
            ]
            font = None
            for fc in font_candidates:
                if Path(fc).exists():
                    try:
                        font = ImageFont.truetype(fc, font_size)
                        break
                    except Exception:
                        continue
            if font is None:
                font = ImageFont.load_default()

            cover_chars = list(title or "")
            if not cover_chars:
                cover_chars = [""]

            def get_text_size(text):
                bbox = draw.textbbox((0, 0), text, font=font)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]

            char_heights = []
            char_widths = []
            for ch in cover_chars:
                cw, ch_h = get_text_size(ch)
                char_widths.append(cw)
                char_heights.append(ch_h)

            line_gap = int(font_size * 0.15)
            total_h = sum(char_heights) + line_gap * (len(cover_chars) - 1)
            start_y = (self.height - total_h) // 2
            current_y = start_y
            for i, ch in enumerate(cover_chars):
                cw = char_widths[i]
                x = (self.width - cw) // 2
                for dx, dy in [
                    (-3, 0), (3, 0), (0, -3), (0, 3),
                    (-2, -2), (2, -2), (-2, 2), (2, 2),
                ]:
                    draw.text((x + dx, current_y + dy), ch, font=font, fill=(0, 0, 0))
                draw.text((x, current_y), ch, font=font, fill=(255, 255, 255))
                current_y += char_heights[i] + line_gap

            bg.save(str(cover_img_path), "PNG")
        except Exception as e:
            logger.error("Pillow 封面生成失败: %s", e, exc_info=True)
            return False

        cmd1 = [
            self.ffmpeg_path,
            "-loop", "1", "-framerate", str(self.fps), "-i", str(cover_img_path),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(cover_duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-profile:v", "baseline", "-level", "3.1",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            "-r", str(self.fps), "-y",
            str(cover_clip),
        ]
        r1 = subprocess.run(cmd1, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        if r1.returncode != 0:
            logger.error("封面视频生成失败: %s", r1.stderr[-300:])
            return False

        cmd2 = [
            self.ffmpeg_path,
            "-i", str(cover_clip), "-i", str(video_path),
            "-filter_complex",
            "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[v][a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "2",
            "-r", str(self.fps), "-y",
            str(output_path),
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        if r2.returncode != 0:
            logger.error("封面拼接失败，使用不带封面的版本")
            import shutil
            shutil.copy2(video_path, output_path)
            return True

        logger.info("封面插入成功（%ss）: %s", cover_duration, output_path)
        return True

    def _replace_audio(self, video_path, audio_path, output_path, duration=None):
        """替换视频音频"""
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path), "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac",
            "-map", "0:v:0", "-map", "1:a:0",
        ]
        if duration is not None:
            cmd += ["-t", str(duration)]
        cmd += ["-y", str(output_path)]

        result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_KWARGS)
        if result.returncode != 0:
            logger.error("音频替换失败: %s", result.stderr)
            return False
        return True

    def compose(
        self, segments, timestamps=None, resolution=None, fps=None,
        bgm_path=None, bgm_volume=30, output_dir=None, index=1,
    ):
        """
        完整的视频合成方法。

        :param segments:    分段列表，每项含 folder_path 和 audio_path
        :param timestamps:  TTS 词级时间戳
        :param resolution:  输出分辨率
        :param fps:         输出帧率
        :param bgm_path:    BGM 文件路径
        :param bgm_volume:  BGM 音量
        :param output_dir:  输出目录
        :param index:       当前生成序号
        :return:            输出视频路径
        """
        logger.info("=" * 60)
        logger.info("开始合成视频 #%d", index)
        logger.info("=" * 60)

        if resolution:
            self.resolution = resolution
            res_part = resolution.split(" ")[0]
            self.width, self.height = map(int, res_part.split("x"))
        if fps:
            self.fps = fps
        if output_dir:
            self.output_dir = Path(output_dir)
            os.makedirs(self.output_dir, exist_ok=True)

        segment_folders = []
        for seg in segments:
            segment_folders.append(seg.get("folder_path", ""))

        tts_path = None
        if segments and "audio_path" in segments[0]:
            tts_path = segments[0]["audio_path"]

        if tts_path:
            tts_path = str(Path(tts_path))

        if not tts_path or not Path(tts_path).exists():
            fallback_path = get_app_dir() / "temp" / "tts_output.mp3"
            if fallback_path.exists():
                tts_path = str(fallback_path)
            else:
                raise Exception(f"TTS 音频文件不存在: {tts_path}")

        _transition_type = config.get("transition_type", "none")
        _transition_duration = (
            (0.3 if _transition_type == "fade_03" else 0.5)
            if _transition_type != "none"
            else 0.0
        )

        segment_videos = []
        for i, seg in enumerate(segments):
            duration = seg["end"] - seg["start"]
            if duration <= 0:
                duration = 1.0
                seg["end"] = seg["start"] + duration
            is_last = i == len(segments) - 1
            if not is_last and _transition_duration > 0:
                duration += _transition_duration

            folder = segment_folders[i] if i < len(segment_folders) else ""
            if not folder:
                raise Exception(f"分段 {i+1} 未配置素材文件夹")
            if not Path(folder).exists():
                raise Exception(f"素材文件夹不存在: {folder}")

            videos = self._scan_video_folder(folder)
            if not videos:
                raise Exception(f"分段 {i+1} 素材文件夹为空")

            selected_video = random.choice(videos)
            seg_output = self.temp_dir / f"seg_{i}.mp4"
            success = self._crop_video_segment(
                selected_video, seg_output, duration, all_videos=videos
            )
            if not success:
                raise Exception(f"分段 {i+1} 视频处理失败")
            segment_videos.append(str(seg_output))

        # 拼接视频
        concat_output = self.temp_dir / "concat_output.mp4"
        transition_type = config.get("transition_type", "none")
        if transition_type == "none" or len(segment_videos) == 1:
            success = self._concat_videos(segment_videos, concat_output)
        else:
            transition_duration = 0.3 if transition_type == "fade_03" else 0.5
            BATCH_SIZE = 8
            if len(segment_videos) <= BATCH_SIZE:
                success = self._concat_videos_with_transition(
                    segment_videos, concat_output, transition_duration
                )
            else:
                batches = [
                    segment_videos[i : i + BATCH_SIZE]
                    for i in range(0, len(segment_videos), BATCH_SIZE)
                ]
                batch_outputs = []
                for bi, batch in enumerate(batches):
                    batch_out = self.temp_dir / f"batch_{bi:03d}.mp4"
                    ok = self._concat_videos_with_transition(
                        batch, batch_out, transition_duration
                    )
                    if not ok:
                        raise Exception(f"第 {bi+1} 批视频拼接失败")
                    batch_outputs.append(batch_out)
                if len(batch_outputs) == 1:
                    import shutil
                    shutil.copy2(str(batch_outputs[0]), str(concat_output))
                    success = True
                else:
                    success = self._concat_videos(batch_outputs, concat_output)
        if not success:
            raise Exception("视频拼接失败")

        concat_video_duration = self._get_video_duration(str(concat_output))

        # 混合音频
        total_duration = segments[-1]["end"]
        mixed_audio = self.temp_dir / "mixed_audio.mp3"
        success = self._mix_audio(tts_path, bgm_path, bgm_volume, mixed_audio, total_duration)
        if not success:
            raise Exception("音频混合失败")

        # 补齐视频时长
        if concat_video_duration < total_duration - 0.2:
            gap = total_duration - concat_video_duration
            filled = False
            last_folder = None
            for folder in reversed(segment_folders):
                if folder and Path(folder).exists():
                    last_folder = folder
                    break
            if last_folder:
                extra_videos = self._scan_video_folder(last_folder)
                if extra_videos:
                    extra_video = random.choice(extra_videos)
                    extra_seg = self.temp_dir / "extra_segment.mp4"
                    ok = self._crop_video_segment(
                        extra_video, extra_seg, gap, all_videos=extra_videos
                    )
                    if ok:
                        extended_output = self.temp_dir / "concat_extended.mp4"
                        ok = self._concat_videos(
                            [str(concat_output), str(extra_seg)], extended_output
                        )
                        if ok:
                            concat_output = extended_output
                            filled = True
            if not filled:
                padded_output = self.temp_dir / "concat_padded.mp4"
                pad_ok = self._pad_video_end(concat_output, padded_output, gap)
                if pad_ok:
                    concat_output = padded_output

        # 替换音频
        video_with_audio = self.temp_dir / "video_with_audio.mp4"
        success = self._replace_audio(
            concat_output, mixed_audio, video_with_audio, duration=total_duration
        )
        if not success:
            raise Exception("音频替换失败")

        # 生成字幕并烧录
        from .subtitle import SubtitleGenerator

        subtitle_gen = SubtitleGenerator(self.resolution)
        subtitle_path = self.temp_dir / "subtitle.ass"

        if timestamps and len(timestamps) > 0:
            subtitle_gen.generate_from_timestamps(timestamps, str(subtitle_path))
        else:
            subtitle_gen.generate_from_segments(
                segments,
                segments[-1]["end"] if segments else 10.0,
                str(subtitle_path),
            )

        final_output = self.output_dir / f"output_{index:03d}.mp4"
        i = index
        while final_output.exists():
            i += 1
            final_output = self.output_dir / f"output_{i:03d}.mp4"

        success = self._burn_subtitle(video_with_audio, str(subtitle_path), final_output)
        if not success:
            import shutil
            shutil.copy2(video_with_audio, final_output)
            logger.warning("字幕烧录失败，使用不带字幕的版本")

        logger.info("=" * 60)
        logger.info("视频合成完成: %s", final_output)
        logger.info("=" * 60)

        return str(final_output)

    def _clean_temp_files(self):
        """清理临时目录文件"""
        count = 0
        for file in self.temp_dir.glob("*"):
            if file.is_file():
                if file.name in ["tts_output.mp3", "tts_timestamps.json"]:
                    continue
                try:
                    os.remove(file)
                    count += 1
                except Exception as e:
                    logger.warning("无法删除临时文件 %s: %s", file, e)
        logger.debug("已清理 %d 个临时文件", count)
