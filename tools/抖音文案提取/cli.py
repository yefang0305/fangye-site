from __future__ import annotations

from pathlib import Path
import sys

from config import parse_args, discover_videos, write_outputs
from asr_engine import LocalWhisperASREngine, LocalASRError
from rule_cleaner import clean_transcript_rules


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        videos = discover_videos(args.input, args.ext)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    if not videos:
        print(f"[提示] 未找到视频文件: {args.input}")
        return 0

    print(f"[发现] {len(videos)} 个视频文件")

    engine = LocalWhisperASREngine(
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        language=args.language,
        model_dir=args.model_dir,
    )

    output_dir = Path(args.output_dir).resolve()
    ok = 0
    fail = 0

    for video in videos:
        print(f"\n[转录] {video.name}")
        try:
            result = engine.transcribe(str(video))
        except LocalASRError as exc:
            print(f"  [失败] {exc}", file=sys.stderr)
            fail += 1
            continue

        raw = result["raw_text"]
        cleaned = raw if args.no_clean else clean_transcript_rules(raw)

        files = write_outputs(
            output_dir=output_dir,
            stem=video.stem,
            raw_text=raw,
            cleaned_text=cleaned,
            segments=result["segments"],
            language=result["language"],
            duration=result["duration"],
        )
        print(f"  [完成] {video.stem}.txt / .md / .json → {output_dir}")
        ok += 1

    print(f"\n[总结] 成功 {ok} 个, 失败 {fail} 个")
    return 1 if fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
