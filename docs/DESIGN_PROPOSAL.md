# Draft design proposal: optional final-render neural finishing

**Codex-assisted preparation material for Jason Lok to review and express in his
own words. Not a maintainer-approved design or a submitted proposal.**

## Problem and demonstrated need

A production Cycles workflow required final-image neural processing guided by
depth and motion vectors. Beauty motion blur and vector-guide export need
different capture settings. Processing outside Blender also requires explicit
camera-cut resets, recoverable shot history and clear separation of originals.

Existing BlenDLSS provides a compositor node, Render Properties controls and the
native bridge used here. Existing Blender development includes DLSS viewport
denoising controls. The proposal concerns generative finishing of final renders,
not replacement or rebranding of those contributions.

## Proposed experiment

An opt-in Render Properties panel sends an immutable scene snapshot and settings
to a separate local worker. The worker serializes beauty capture, blur-off guide
capture and native neural evaluation. Original EXRs are retained; processed SDR
PNGs are separate. The panel exposes still/animation mode, artistic controls,
cancel/resume, status and original/processed viewing.

The native patch contains no model binaries and does not require importing GPU
code during Blender startup. Unsupported platforms keep ordinary rendering
available. The current backend is Windows-only and experimental. Its prerelease,
community-modified runtime is not proposed as a Blender dependency for shipping.
A separate experimental package documents and includes the exact local backend.

## Feedback sought

Whether this workflow belongs in core Blender or an extension; whether Render
Properties is an appropriate entry point; whether a worker boundary is useful;
and what supported backend and color-management requirements would be needed for
a mergeable implementation. This is a design discussion before a shipping feature.

## Evidence and remaining work

Non-rendering tests cover cancellation, interrupted-shot recovery, camera-cut
state, dimensions, hashes, locking, unavailable runtime and native error
propagation with fixtures. The exact native modules register in Blender 5.2.2.

The new demo has not been rendered. End-to-end native inference, current-main
build/startup, visual quality, depth reprojection and cross-platform startup are
pending. Previous project runtime successes must not be presented as those tests.

## Separate usability proposal

Explain the disabled Vector pass immediately below its control when Motion Blur
is enabled in Cycles and EEVEE. Current code disables the control without an
inline explanation. This is independently useful to motion-vector compositing
workflows and does not introduce neural processing or NVIDIA dependencies.
