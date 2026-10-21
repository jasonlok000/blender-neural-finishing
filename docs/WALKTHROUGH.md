# Human review walkthrough

This is a preparation aid, not an assertion that human review has happened.

1. In the patch, inspect the Render Properties panel and its default-off setting.
   Confirm that drawing it and ordinary F12 do not launch processing.
2. Inspect `RENDER_OT_neural_finishing`: its preflight rejects an active render,
   unsupported scenes and unavailable worker packages before writing a snapshot.
   Check the snapshot/output location and source preservation behavior.
3. Inspect the file-only probe. It does not load the NVIDIA library; an actual
   successful frame evaluation is a different milestone.
4. Follow `job.json` into the worker and `render_capture.py`. Beauty retains
   motion blur; guides disable it. Compositor File Output nodes are muted only in
   the worker copy. Confirm that outputs go into the job directory.
5. Follow depth/motion conversion into the BlenDLSS bridge. The adapter passes
   native scene data and checks evaluation returns. It is not a trained model or
   a source implementation of NVIDIA's model.
6. Inspect shot grouping, history resets, output receipts and OS locking. Explain
   why an interrupted shot must start again even if some PNGs already exist.
7. Inspect the compatibility adapter. It modifies architecture-query behavior
   only inside the worker process and restores it during cleanup. This is an
   experimental hardware path, not official RTX 3090 support.
8. Read the test report and distinguish synthetic fixture results, module
   registration checks, prior runtime evidence and deferred end-to-end testing.
9. When production rendering has finished and testing is explicitly wanted,
   render the still and 48-frame demo. Watch the cut, compare thin edges and
   reflections, test cancel/resume, and confirm source and original HDR files
   remain intact. Record actual configuration, timings and results.
10. Write your own proposal/PR description, explaining the contribution and known
    limits. Review the code and describe the AI-assisted methodology. Accept any
    contributor agreement personally if required by Blender Projects.

Blender's policy requires contributors to understand and manually review their
submission and carefully test functionality. It also asks contributors to write
their own submission descriptions/comments. This walkthrough supports that work;
it does not replace it:
https://developer.blender.org/docs/handbook/contributing/ai_contributions/

## Contribution wording

- Public prototype: "I developed an experimental neural-finishing integration for Blender."
- Submitted official PR: "I submitted a contribution to Blender," linked to that PR.
- Accepted official change: "I contributed to Blender," linked to the merged change.

A GitHub experiment or fork is not a merged official Blender contribution.
