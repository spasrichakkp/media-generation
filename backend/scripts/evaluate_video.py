"""Generate one real clip and save reproducible evaluation metadata.

Run from the repository root:
PYTHONPATH=backend .venv/bin/python backend/scripts/evaluate_video.py --prompt "..."
This makes one real inference request and can consume provider credits.
"""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import time

from src.config import get_settings
from src.infrastructure.services.video_generator_factory import create_video_generator


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', required=True)
    parser.add_argument('--model', choices=['wan-2.2-api', 'wan-2.2-local'], default='wan-2.2-api')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--aspect-ratio', choices=['16:9', '9:16'], default='16:9')
    parser.add_argument('--output', type=Path, default=Path('artifacts/video-evaluation/sample.mp4'))
    args = parser.parse_args()
    settings = get_settings()
    generator = create_video_generator(settings, None, args.model)
    started = time.monotonic()
    path = None
    try:
        path = await generator.generate_video(args.prompt, parameters={
            'duration':5, 'seed':args.seed, 'aspect_ratio':args.aspect_ratio,
        })
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, args.output)
        from moviepy import VideoFileClip
        with VideoFileClip(str(args.output)) as clip:
            metadata = {'prompt':args.prompt, 'model':args.model, 'seed':args.seed,
                        'aspect_ratio':args.aspect_ratio, 'duration':clip.duration,
                        'size':clip.size, 'fps':clip.fps, 'elapsed_seconds':round(time.monotonic()-started, 2)}
        args.output.with_suffix('.json').write_text(json.dumps(metadata, indent=2)+'\n')
        print(f'Video: {args.output.resolve()}')
    except Exception as exc:
        # Provider errors can contain request metadata: redact the configured credential.
        message = str(exc)
        if settings.hf_token:
            message = message.replace(settings.hf_token, '[REDACTED]')
        raise SystemExit(f'Generation failed: {message}') from None
    finally:
        if path:
            await generator.cleanup_temp_files(path)


if __name__ == '__main__':
    asyncio.run(main())
