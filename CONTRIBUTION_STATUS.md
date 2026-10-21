# Contribution status

- Experimental integration: implemented as source and a portable Windows package.
- Native source branch: https://github.com/jasonlok000/blender-neural-finishing-core/tree/codex/neural-finishing-prototype
- Independent usability branch: https://github.com/jasonlok000/blender-neural-finishing-core/tree/codex/vector-pass-explanation
- Source, protocol and documentation: https://github.com/jasonlok000/blender-neural-finishing
- Automated validation: non-rendering fixture tests, syntax and native module registration only.
- Demo scene: prepared and saved; no images or neural results rendered for this prototype.
- Official Blender design discussion / PR: **not submitted**. Blender Projects
  sign-in and human review are pending. Draft preparation material is in docs/.
- Official acceptance / merge: **not achieved**.

The user explicitly requested no rendering validation during an existing
production render. No live inference was started either. The test suite does not
load NVIDIA code, and merely opening the native preview does not start work.

Before an upstream submission, complete the human review walkthrough and write
the proposal/PR description in your own words. End-to-end testing must wait until
rendering is explicitly wanted and the production job is no longer active.

The separate Vector-pass explanation is a four-line interface improvement. It is
not evidence of acceptance until it is actually reviewed and merged upstream.
