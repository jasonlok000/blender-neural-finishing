# Neural Finishing for Blender — experimental native prototype

A native Render Properties prototype for generative finishing of final Cycles
renders. It submits a copied scene to an isolated worker, retains original HDR
renders and writes separate SDR neural results. It is not viewport denoising,
upscaling or frame generation.

**Status: source and portable experimental package prepared; non-rendering checks
passed. End-to-end rendering and neural inference for this new integration are
NOT YET VALIDATED. No official Blender PR has been submitted or merged.**

The contributor is Jason Lok. Code and documentation were prepared with OpenAI
Codex assistance. Human review and artist-facing acceptance are still pending.
The workflow is based on production experience and uses the upstream BlenDLSS
bridge; neither the NVIDIA model nor the original BlenDLSS interface is our work.

## Try the interface without rendering

1. Extract the complete experimental Windows release ZIP.
2. Run `Open_Native_Preview.cmd` (or pass your Blender executable as its first
   argument). This opens a separate stock Blender session with the exact native
   patch modules registered temporarily. It does not install or alter Blender.
3. Under Render Properties, expand **Neural Finishing (Experimental)**.
   The feature starts disabled. Opening the interface does not render or load
   the NVIDIA library. **Verify Worker Files** checks hashes only, without GPU
   initialization. `Verify_Files_Only.cmd` performs the same file-only check.
4. **Do not press Render & Process while another render is running.** The panel
   also refuses to start when it detects a background Blender render.

The preview is a session loader for reviewing the interface. Native source
changes live in the accompanying Blender patch, not an installed add-on or an
official Blender build. Settings are session-only in this WIP.

## Explicit rendering and processing — after existing work finishes

When ready for the deferred tests, enable the feature, choose Current Frame or
Frame Range, select an output folder, and press **Render & Process**. The bundled
demo contains 48 frames, two perspective cameras and a cut at frame 25. It uses
CPU Cycles rendering at 1280 x 720, 32 samples; neural inference uses the GPU.
No demo frames were rendered during preparation of this release.

Each job has its own `scene.blend`, `job.json`, original 32-bit multilayer EXRs,
display-transformed beauty PNGs, blur-off depth/motion guides, metadata and
separate processed PNGs. Original/Processed buttons display the selected frame.
Ordinary F12 rendering is untouched. Compositor File Output nodes are muted in
the isolated worker to avoid overwriting unrelated outputs.

Cancel signals only this job. Resume Last Job retains verified captures and
complete shots; an incomplete neural shot restarts at its first frame to rebuild
history. Camera markers reset history, including cuts between markers using the
same camera. Snapshot, captured-file, external-image and runtime hashes guard
against reusing changed inputs. Native failures are errors; no approximation
backend is selected automatically.

Version one supports Windows, Cycles, opaque uncropped output, perspective
cameras, consecutive frames and one active view layer. Linked libraries,
image sequences, tiled/movie textures and Video Sequencer output are rejected.
Other external simulation dependencies have not been qualified. Depth of field,
reflections, disocclusions and material animation still need visual assessment.

The current interface is RGBA8 SDR. Higher-bit-depth containers would not restore
HDR precision, and this project makes no HDR neural-output claim. A more
photographic result is not a physically recomputed relight or a fidelity guarantee.

## Backend provenance

The experimental ZIP intentionally includes the exact working community-modified
NVIDIA `nvngx_dlssnr.dll` 310.8.0.0, the BlenDLSS ABI-3 bridge and the independent
process-local Ampere compatibility adapter. The runtime originated as a leaked,
non-public build. Redistribution permission is unresolved; documenting its origin
does not grant permission. This is neither an NVIDIA-supported runtime nor an
official Blender feature. See `THIRD_PARTY.md` and `runtime-manifest.json`.

Prior tests of those binary hashes succeeded on an RTX 3090 24GB with driver
580.97 in a different, existing processing pipeline. Those results are not a
validation of this new integration. Other GPUs and drivers are untested here.
The current compatibility adapter is restricted to a single Ampere GPU. It
affects only its worker process; no driver or system configuration is changed.

## Development and contribution

Run `python -m unittest discover -s tests -v` and `python tools/verify_source.py`.
These use synthetic test images and an explicitly injected test backend; no
Blender rendering or NVIDIA inference is performed. The fixture backend is not
available from the public worker command line or Blender panel.

See `docs/PROTOCOL.md`, `docs/DESIGN_PROPOSAL.md`, `docs/WALKTHROUGH.md` and
`docs/VALIDATION.md`. The source patch targets Blender main at the pinned base
recorded in `docs/UPSTREAM.md`. Initial module registration was checked in stock
Blender 5.2.2 LTS, not a compiled development build.

The source-only Blender submission excludes third-party binaries. A WIP can be
discussed before all implementation questions are resolved, but it must clearly
state incomplete testing and cannot claim official acceptance.
