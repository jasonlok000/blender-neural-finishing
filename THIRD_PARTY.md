# Third-party components and attribution

New toolkit code: Jason Lok, GPL-3.0-or-later. Native Blender patch modules:
GPL-2.0-or-later. Codex assisted with implementation and documentation; human
review remains required before an upstream Blender submission.

## BlenDLSS

The bridge and its C ABI are by LGCY Creative Studios / ProdbyLGCY:
https://github.com/ProdbyLGCY/BLENDLSS

Pinned commit: b4a62f77ef2de2cbc610be7fee344d1c0854b241. The upstream extension
manifest declares GPL-3.0-or-later. Its original native source and manifest are
retained in `third_party/blendlss/`. We do not claim authorship of its compositor
node, Render Properties panel, native bridge or NVIDIA integration discovery.
The precompiled bridge is from the upstream release. A reproducible build match
between that DLL and the retained source has not been established.

## NVIDIA runtime

Copyright NVIDIA. The modified `nvngx_dlssnr.dll` 310.8.0.0 came from the
NeuralScreen community release at repository commit
4a9ee16d486668099a12296eabaa9ffe34704744:
https://github.com/perseval-BLR/NeuralScreen

It is a leaked, non-public runtime with community hardware-compatibility
modifications. Its publisher signature does not validate. The pinned hash is
recorded in `runtime-manifest.json`. Prior binary inspection found matching
NVIDIA model weights, not proof of numerical equivalence on supported hardware.

The experimental download includes this exact binary at the contributor's
request. No redistribution grant for it has been established. The upstream
runtime-provenance notice is retained in `third_party/notices/`. No NeuralScreen
application source, application executable or application license is incorporated
as a license grant for this NVIDIA file.

NVIDIA's public SDK license is retained as a reference only. It does not establish
permission for this specific modified runtime. NVIDIA and Blender do not endorse
this project.

## Python and packages

Portable CPython 3.13.5 comes from python.org's Windows embeddable distribution;
the Python license ships with it. NumPy, Pillow and OpenEXR package metadata and
license texts are retained with their installed distributions under
`runtime/Lib/site-packages/`. Versions are pinned in `requirements-pinned.txt`.

The demo scene contains Blender-generated primitive geometry, including Suzanne,
and procedural materials. It contains no Formula3 production files or branding.
