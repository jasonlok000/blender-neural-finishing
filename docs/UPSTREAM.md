# Upstream baseline and comparison

Native target: official Blender GitHub mirror, main branch, base commit
`6421771fd4d65965a2259e14d222f4913f192d03` (Sculpt: Adjust color attribute painting).
The actual upstream contribution destination is Blender Projects, not the GitHub
mirror. Neither patch has been accepted or merged upstream.

The native prototype adds startup Python operators and a Render Properties panel.
No render-engine C++ code, DNA structures, F12 handler or model binaries change.
The source targets this development base; module-level checks use stock 5.2.2.

Reviewed overlap:

- Blender main already has DLSS viewport-denoising controls in Cycles. This
  contribution is final-render generative finishing with an external worker.
- ProdbyLGCY/BLENDLSS already has a Render Properties panel and compositor node.
  It supplies the native bridge used here. The new UI location itself is not a
  claimed invention. Pinned upstream source attribution is in THIRD_PARTY.md.
- Other experimental DLSS 5 integrations exist, including
  https://github.com/senamh/DLSS-5-for-Blender. There is no claim to be the first.
- Searches did not establish that an equivalent final-finishing design is already
  accepted by Blender. Maintainer discussion is still necessary.

Blender's current Cycles and EEVEE pass panels disable Vector when motion blur is
on. The separate usability patch adds an inline explanation, preserving the
existing restriction rather than attempting simultaneous motion-blur/vector
rendering. Existing feature requests about enabling both are different work.

Contribution process:
https://developer.blender.org/docs/handbook/contributing/

AI-assisted contribution policy:
https://developer.blender.org/docs/handbook/contributing/ai_contributions/
