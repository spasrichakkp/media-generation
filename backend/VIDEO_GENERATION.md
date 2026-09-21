# Real video generation

The default renderer is **Wan 2.2 A14B through Hugging Face Inference Providers (fal-ai)**.
It creates moving imagery from the visual prompt. The old renderer drew colored backgrounds
and text; the previous local Wan adapter also discarded its generated frames. Those silent
fallbacks have been removed from the Wan path. `moneyprinter-turbo` remains an explicit
legacy slideshow option; `luma-dream-machine` is rejected because it has no adapter.

## Hosted setup (including Macs)

Install `backend/requirements.txt`. Put these values in the git-ignored `backend/.env`:

```dotenv
VIDEO_PROVIDER=huggingface_api
HF_TOKEN=<Hugging Face token with Inference Providers permission>
HF_VIDEO_API_MODEL=Wan-AI/Wan2.2-T2V-A14B
HF_VIDEO_TIMEOUT=900
```

Docker Compose loads this file for both API and worker. Rebuild/restart those services after
installing dependencies. `HF_VIDEO_TIMEOUT` configures SDK request timeout; the Celery task
hard limit also applies. The SDK's provider queue polling is not an overall deadline.
Do not automatically retry failed paid jobs: a timed-out remote generation may still finish.
Automatic exception retries are disabled for video tasks.

Example job:

```json
{
  "content_type": "video",
  "model_name": "wan-2.2-api",
  "prompt": "Photorealistic ocean waves breaking onto wet sand at sunset, sparkling foam, natural water motion, slow camera push forward.",
  "parameters": {"duration": 5, "aspect_ratio": "9:16", "seed": 123}
}
```

Supported parameters: `duration` (1–5 seconds), `aspect_ratio` (`16:9` or `9:16`),
`seed` (0–2147483647), `num_inference_steps` (20–60), `negative_prompt`, and optional
`narration`. Narration must fit the shot; the generator rejects overlong speech instead of
freezing or looping visuals. Audio is off by default. Duration is rounded to the model's
frame-count constraints. Hosted output is 720p; do not pass legacy `width`, `height`, `fps`,
`resolution`, or `background_color`. Invalid parameters are rejected before enqueuing.
For longer stories, generate separate shots; this change does not promise consistent
characters or seamless continuity between independent clips.

The API and worker honor the requested model. If omitted on job creation, `VIDEO_PROVIDER`
selects the default. An HF token alone does not silently change an explicit model selection.
Failures, invalid files and solid-color output fail the job; they never become slide videos.
Blank-frame checks are not a semantic quality or anatomy score.

## Local open-weight option

Use an NVIDIA CUDA worker, install `backend/requirements-video-local.txt` after the base
requirements, set `VIDEO_PROVIDER=huggingface`, and select `wan-2.2-local`.
The checkpoint is `Wan-AI/Wan2.2-TI2V-5B-Diffusers`; expect substantial model downloads,
RAM and GPU memory use (plan for a 24 GB GPU and CPU offload). CPU/Mac inference is not
supported by this adapter. Weights load lazily and are reused within the worker process.
Run one worker process per GPU to avoid loading competing copies. Actual `.frames[0]`
output is encoded at 24 fps. No API fee applies locally, but hardware and electricity do.

## Repeatable quality checks

From repository root:

```sh
PYTHONPATH=backend .venv/bin/python backend/scripts/evaluate_video.py \
  --prompt "Photorealistic fox walking through a forest, natural movement, morning light" \
  --seed 42 --output artifacts/video-evaluation/fox.mp4
PYTHONPATH=backend .venv/bin/python -m pytest \
  backend/tests/unit/test_huggingface_video_generator.py \
  backend/tests/unit/test_video_worker_routing.py -o addopts='' -q
```

The evaluation command makes a real request and writes video plus JSON metadata. Compare
prompt adherence, subject anatomy, motion, temporal consistency and camera movement across
fixed seeds before changing defaults. Mocked tests verify encoding, routing, invalid input,
upload failures and absence of fallback; they do not prove generative quality.

S3 uploads use the existing storage adapter and presigned download URLs (one-hour expiry).
For Docker MinIO, `S3_PUBLIC_ENDPOINT_URL=http://localhost:9000` produces browser-reachable
URLs while uploads use the internal service hostname. Set a reachable public endpoint in
remote deployments. The bucket must already exist. URL refresh is not implemented here.

## Sources and cost

- [Hugging Face text-to-video API](https://huggingface.co/docs/inference-providers/tasks/text-to-video)
- [Wan 2.2 A14B provider schema](https://fal.ai/models/fal-ai/wan/v2.2-a14b/text-to-video/api)
- [Diffusers Wan pipelines](https://huggingface.co/docs/diffusers/api/pipelines/wan)
- [Hugging Face pricing](https://huggingface.co/docs/inference-providers/pricing)

Hugging Face offers limited monthly credits; hosted generation beyond credits is billed.
This is not an unlimited free API. Model/provider availability was verified against the
Hugging Face model API during implementation. No external benchmark establishes that this
model is universally best; it is a working realistic-video replacement for this product.

## Verification in this workspace

Two live hosted requests succeeded: a landscape fox and portrait ocean, each 5.03 seconds,
720p, 32 fps (provider interpolation). Videos and seed/prompt metadata are under
`artifacts/video-evaluation/`. Sampled frames showed the requested subjects, motion and no
text overlays. The generated fox video was uploaded to MinIO and its presigned download
verified byte-for-byte. A third request through POST /api/v1/jobs reached the real Celery
worker and provider, but returned HTTP 402 because included credits were exhausted; GET
job status correctly reported failed with no result URL. No full successful API-to-provider-
to-storage job was possible after that limit. Local CUDA inference was not run on this Mac.

Docker API, worker, PostgreSQL, Redis and MinIO were started locally. The MinIO image was
updated to an available pinned Quay release after the previous Docker Hub image failed to
pull. API import errors, timezone-aware quota comparison and commit-before-enqueue were
fixed to unblock the job flow. Additional hosted evaluation requires available credits.
