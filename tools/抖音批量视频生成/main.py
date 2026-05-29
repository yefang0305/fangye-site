"""
main.py - 抖音批量视频生成工具入口
─────────────────────────────────
提供命令行接口，支持：
  1. TTS 语音合成（文本 → 音频 + 时间戳）
  2. 文案分段（基于时间戳 或 AI 智能分段）
  3. 视频合成（音频 + 素材 + BGM + 字幕 → 视频）
  4. 批量任务管理

使用方式：
  python main.py tts --text "你的文案" --output ./output
  python main.py compose --segments segments.json --audio ./audio.mp3
  python main.py batch --tasks tasks.json
"""

import sys
import os
import argparse
import json
import logging
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config
from core.tts import TTSGenerator, TTSAuthError, TTSNetworkError, TTSParamError
from core.text_segmenter import segment_by_text
from core.subtitle import SubtitleGenerator
from core.video_composer import VideoComposer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def cmd_tts(args):
    """TTS 语音合成命令"""
    if not args.text and not args.file:
        print("错误: 请提供 --text 或 --file 参数")
        sys.exit(1)

    text = args.text
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")

    generator = TTSGenerator()
    print(f"正在合成语音，文案长度: {len(text)} 字...")

    try:
        audio_path, timestamps = generator.generate(
            text,
            speed=args.speed,
            voice=args.voice or None,
            volume=args.volume,
            progress_callback=lambda p, m: print(f"  [{p}%] {m}"),
        )
        print(f"音频已生成: {audio_path}")
        print(f"时间戳条目: {len(timestamps)}")

        # 保存时间戳
        if args.output:
            ts_file = Path(args.output) / "timestamps.json"
            ts_file.parent.mkdir(parents=True, exist_ok=True)
            ts_file.write_text(
                json.dumps(timestamps, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"时间戳已保存: {ts_file}")

    except TTSAuthError as e:
        print(f"鉴权失败: {e}")
        sys.exit(1)
    except TTSNetworkError as e:
        print(f"网络错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"合成失败: {e}")
        sys.exit(1)


def cmd_segment(args):
    """文案分段命令"""
    if not args.timestamps_file:
        print("错误: 请提供 --timestamps-file 参数（TTS 生成的时间戳 JSON 文件）")
        sys.exit(1)

    ts_data = json.loads(Path(args.timestamps_file).read_text(encoding="utf-8"))
    timestamps = ts_data if isinstance(ts_data, list) else ts_data.get("timestamps", [])

    audio_duration = args.audio_duration
    if not audio_duration and timestamps:
        audio_duration = timestamps[-1].get("end_time", 0)

    min_duration = args.min_duration or config.get("text_segment_min_duration", 1.8)
    segments = segment_by_text(timestamps, min_duration, audio_duration)

    print(f"分段完成，共 {len(segments)} 段：")
    for i, seg in enumerate(segments):
        print(
            f"  [{i+1}] {seg['start']:.2f}s - {seg['end']:.2f}s "
            f"({seg['duration']:.2f}s): {seg['text'][:40]}..."
        )

    if args.output:
        out_file = Path(args.output) / "segments.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            json.dumps(segments, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"分段已保存: {out_file}")


def cmd_compose(args):
    """视频合成命令"""
    if not args.segments:
        print("错误: 请提供 --segments 参数（分段 JSON 文件路径）")
        sys.exit(1)

    segments_data = json.loads(Path(args.segments).read_text(encoding="utf-8"))

    # 支持两种格式：纯分段列表 或 完整任务配置
    if isinstance(segments_data, list):
        segments = segments_data
        audio_path = args.audio
        bgm_path = args.bgm
        bgm_volume = args.bgm_volume
    else:
        segments = segments_data.get("segments", [])
        audio_path = segments_data.get("audio_path", args.audio)
        bgm_path = segments_data.get("bgm_path", args.bgm)
        bgm_volume = segments_data.get("bgm_volume", args.bgm_volume)

    if not segments:
        print("错误: 分段数据为空")
        sys.exit(1)

    composer = VideoComposer()
    print(f"开始合成视频，共 {len(segments)} 段...")

    try:
        output_path = composer.compose(
            segments=segments,
            timestamps=None,
            resolution=args.resolution,
            fps=args.fps,
            bgm_path=bgm_path,
            bgm_volume=bgm_volume,
            output_dir=args.output_dir,
            index=args.index,
        )
        print(f"视频已生成: {output_path}")
    except Exception as e:
        print(f"合成失败: {e}")
        sys.exit(1)


def cmd_batch(args):
    """批量任务管理命令"""
    if not args.tasks:
        print("错误: 请提供 --tasks 参数（任务配置 JSON 文件路径）")
        sys.exit(1)

    tasks_data = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("tasks", [])

    if not tasks:
        print("错误: 任务列表为空")
        sys.exit(1)

    print(f"批量任务共 {len(tasks)} 个")

    # 执行 TTS（如果任务中有文案）
    tts_gen = TTSGenerator()
    composer = VideoComposer()

    for idx, task in enumerate(tasks):
        print(f"\n{'=' * 50}")
        print(f"任务 {idx + 1}/{len(tasks)}: {task.get('name', f'task_{idx}')}")
        print(f"{'=' * 50}")

        script_text = task.get("script_text", "")
        audio_path = task.get("audio_path", "")
        timestamps = task.get("timestamps", [])

        # 如果提供了文案且无音频，则先合成 TTS
        if script_text and not audio_path:
            print("  合成 TTS...")
            try:
                audio_path, timestamps = tts_gen.generate(
                    script_text,
                    speed=task.get("tts_speed", 1.0),
                    voice=task.get("tts_voice"),
                )
                print(f"  音频: {audio_path}")
            except Exception as e:
                print(f"  TTS 失败: {e}")
                continue

        # 构建分段
        segments = task.get("segments", [])
        if not segments and timestamps:
            audio_dur = task.get("audio_duration") or (
                timestamps[-1].get("end_time", 0) if timestamps else 10
            )
            segments = segment_by_text(
                timestamps,
                config.get("text_segment_min_duration", 1.8),
                audio_dur,
            )
            # 为每个分段附加素材文件夹
            for seg in segments:
                seg["folder_path"] = task.get("material_folder", "")
                seg["audio_path"] = audio_path

        if not segments:
            print("  错误: 无分段数据")
            continue

        # 合成视频
        output_count = task.get("output_count", 1)
        for vi in range(output_count):
            print(f"  生成视频 {vi + 1}/{output_count}...")
            try:
                composer.compose(
                    segments=segments,
                    timestamps=timestamps if task.get("use_timestamps", True) else None,
                    resolution=task.get("resolution"),
                    fps=task.get("fps"),
                    bgm_path=task.get("bgm_path"),
                    bgm_volume=task.get("bgm_volume", 30),
                    output_dir=task.get("output_dir"),
                    index=idx * output_count + vi + 1,
                )
            except Exception as e:
                print(f"  视频生成失败: {e}")
                continue

    print("\n批量任务完成！")


def cmd_config(args):
    """配置管理命令"""
    if args.show:
        print("当前配置:")
        for key, value in sorted(config.config.items()):
            # 隐藏敏感信息
            if any(s in key.lower() for s in ["token", "key", "secret"]):
                value = "***" if value else ""
            print(f"  {key}: {value}")
    elif args.set_key and args.set_value:
        config.set(args.set_key, args.set_value)
        print(f"已设置 {args.set_key} = {args.set_value}")
    else:
        print("用法: python main.py config --show")
        print("      python main.py config --set-key KEY --set-value VALUE")


def main():
    parser = argparse.ArgumentParser(
        description="抖音批量视频生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py tts --text "你好，这是一段测试文案。"
  python main.py segment --timestamps-file timestamps.json
  python main.py compose --segments segments.json --audio audio.mp3
  python main.py batch --tasks tasks.json
  python main.py config --show
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # tts 子命令
    tts_parser = subparsers.add_parser("tts", help="TTS 语音合成")
    tts_parser.add_argument("--text", type=str, help="文案内容")
    tts_parser.add_argument("--file", type=str, help="文案文件路径")
    tts_parser.add_argument("--speed", type=float, default=1.0, help="语速 (0.8-1.5)")
    tts_parser.add_argument("--voice", type=str, help="音色 ID")
    tts_parser.add_argument("--volume", type=int, default=100, help="音量 (50-200)")
    tts_parser.add_argument("--output", type=str, default="./output", help="输出目录")

    # segment 子命令
    seg_parser = subparsers.add_parser("segment", help="文案分段")
    seg_parser.add_argument("--timestamps-file", type=str, required=True, help="TTS 时间戳 JSON 文件")
    seg_parser.add_argument("--audio-duration", type=float, help="音频总时长（秒）")
    seg_parser.add_argument("--min-duration", type=float, help="最短段落时长（秒）")
    seg_parser.add_argument("--output", type=str, default="./output", help="输出目录")

    # compose 子命令
    comp_parser = subparsers.add_parser("compose", help="视频合成")
    comp_parser.add_argument("--segments", type=str, required=True, help="分段 JSON 文件路径")
    comp_parser.add_argument("--audio", type=str, help="TTS 音频文件路径")
    comp_parser.add_argument("--bgm", type=str, help="BGM 文件路径")
    comp_parser.add_argument("--bgm-volume", type=int, default=30, help="BGM 音量 (0-100)")
    comp_parser.add_argument("--resolution", type=str, default="1080x1920", help="输出分辨率")
    comp_parser.add_argument("--fps", type=int, default=30, help="输出帧率")
    comp_parser.add_argument("--output-dir", type=str, default="./output", help="输出目录")
    comp_parser.add_argument("--index", type=int, default=1, help="输出文件序号")

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量任务")
    batch_parser.add_argument("--tasks", type=str, required=True, help="任务配置 JSON 文件")

    # config 子命令
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_parser.add_argument("--show", action="store_true", help="显示当前配置")
    config_parser.add_argument("--set-key", type=str, help="设置配置项键名")
    config_parser.add_argument("--set-value", type=str, help="设置配置项值")

    args = parser.parse_args()

    if args.command == "tts":
        cmd_tts(args)
    elif args.command == "segment":
        cmd_segment(args)
    elif args.command == "compose":
        cmd_compose(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
