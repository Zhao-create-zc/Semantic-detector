# Release Process

Semantic Detector uses semantic version tags such as `v0.1.0`.

## Before tagging

1. Update the package version in `pyproject.toml` and `src/semantic_detector/__init__.py`.
2. Move relevant entries from `CHANGELOG.md` under the new version heading.
3. Run `python -m pytest -q`.
4. Confirm the `tests` and `package` GitHub Actions workflows are green on `main`.
5. Confirm `CITATION.cff` contains the same software version.

## Create the tag

```bash
git tag -a v0.1.0 -m "Semantic Detector v0.1.0"
git push origin v0.1.0
```

Pushing a semantic-version tag triggers `.github/workflows/release.yml`, which builds source/wheel distributions, validates them with Twine, and creates a GitHub Release with generated notes.

A release tag should only be created from a reviewed, green `main` commit.
