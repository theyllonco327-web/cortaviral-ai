# CortaViral AI 1.0 — release candidate

## Implemented in this candidate
- Phrase-boundary quality scoring based on terminal punctuation, trailing connectors and speech continuity.
- Avoids choosing an obviously unfinished speech boundary when the following segment is available and the configured maximum duration leaves room to extend.
- Adds regression tests for the boundary heuristic.

## Validation required before release
- GitHub Actions: backend checks, regression tests and Android debug APK build must pass.
- Install the generated APK on a physical Android device.
- Test gallery upload, supported public URLs, processing progress, completed previews, MP4 downloads, ZIP export and captions.
- Verify the deployed Render API is on the matching commit and remains available during long jobs.

## Known limits
The phrase-boundary detector is a heuristic, not a guarantee of semantic completeness. URL extraction depends on the source platform's access rules. Processing uses the Render backend; this build is not offline.
