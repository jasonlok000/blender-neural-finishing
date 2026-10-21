# Validation status

## Performed without rendering

- 14 automated tests passed using tiny synthetic images, synthetic EXR guide
  channels and an explicitly injected fixture backend. Subprocess launch is
  forbidden inside this suite. No NVIDIA code is loaded.
- Portable CPython 3.13.5 successfully imports the bundled NumPy 2.4.1,
  Pillow 12.3.0 and OpenEXR 3.5.2 packages.
- Runtime and bridge hashes match the existing working pipeline's pinned hashes.
  This is binary identity, not an inference test of the new integration.
- The exact native panel/operators registered and unregistered in stock Blender
  5.2.2 LTS. Registration created no worker. The feature started disabled.
- The file-only probe returned `gpu_tested=false`. The read-only process check
  detected the existing production render, and the guard rejected starting work.
- The demo scene was constructed and saved without rendering. It has 48 frames,
  cameras cut at frame 25, 1280 x 720 output and no production assets.

## Pending — deliberately not started

The user has an active production render and explicitly requested no rendering
validation. Therefore no beauty, guide, thumbnail, comparison-video or inference
job was started for this prototype. In particular:

- Still and full 48-frame end-to-end execution.
- Native frame timing, actual runtime initialization and output inspection.
- Camera-reprojection accuracy and visual temporal coherence on the demo.
- Actual mid-render/mid-inference cancellation and restart behavior.
- Full current-main Blender build/startup and non-Windows application startup.
- Human code review and artist-facing acceptance.

The worker orchestration and recovery assertions currently have fixture evidence
only. Native runtime failures are tested as injected failures, not reproduced
GPU failures. No pixel-quality or performance claim is made.

Automated test details and the non-rendering registration report are retained
under `validation/`. The fixture backend is unavailable from the public UI/CLI.
