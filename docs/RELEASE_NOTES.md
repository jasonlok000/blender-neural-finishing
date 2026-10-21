# 0.1.0 experimental — native interface and worker prototype

This prerelease contains a native Render Properties prototype, an isolated local
worker, source patches, a 48-frame/two-camera demo scene and a portable Windows
package. The complete experimental ZIP includes the exact community-modified
NVIDIA runtime and BlenDLSS bridge, with hashes and provenance notices.

**End-to-end rendering and neural inference for this new integration have not
been run.** Preparation deliberately avoided rendering and GPU inference while
an existing production render was active. Non-rendering fixture tests and native
module registration checks passed. Prior runtime success belongs to an earlier
pipeline and is not a test of this integration.

Extract the ZIP and run `Open_Native_Preview.cmd` to inspect the interface in a
separate Blender session. The feature starts disabled. `Verify_Files_Only.cmd`
does not initialize a GPU. Rendering requires explicitly pressing Render &
Process, and the application refuses to start alongside a detected background
Blender render. No ordinary Blender installation files are modified.

The runtime is a leaked, non-public NVIDIA build with community compatibility
modifications. Redistribution permission remains unresolved. It is included in
this experimental download, not in the Blender source changes. See THIRD_PARTY.md.

No official Blender pull request has yet been submitted or merged. The two source
branches and the human review walkthrough are linked from CONTRIBUTION_STATUS.md.
This release is not an official Blender or NVIDIA product.
