# Repository Guidelines

## Project Structure & Module Organization

Core code lives in `src/red_env/`. Keep CLI entrypoints under `src/red_env/cli/`, manifest parsing under `src/red_env/manifest/`, package assembly under `src/red_env/packaging/`, download logic under `src/red_env/fetchers/`, install metadata under `src/red_env/installer/`, and verification logic under `src/red_env/verification/`. Store package and profile definitions in `manifests/`, static payloads in `assets/`, and container helpers in `docker/`. Put tests in `tests/` and group them by subsystem, for example `tests/manifest/test_loader.py`.

## Build, Test, and Development Commands

Install the project in editable mode with development dependencies:

```bash
python -m pip install -e .[dev]
```

Run the full test suite with `python -m pytest -q`. Validate manifest structure with `python -m red_env manifest lint`. Inspect a profile with `python -m red_env profile show core`. Build an artifact with `python -m red_env build --profile core --arch x86_64`. Verify a built archive with `python -m red_env verify --artifact dist/red_env_core_x86_64.tar.gz --arch x86_64`.

## Coding Style & Naming Conventions

Target Python 3.11+ and use 4-space indentation. Follow the repository’s existing small-module layout: keep files focused on one subsystem responsibility and prefer snake_case for module, function, and test names. Match existing package naming in `manifests/packages/*.toml`. There is no dedicated formatter configured yet, so keep style consistent with surrounding code and avoid unrelated refactors.

## Testing Guidelines

Tests use `pytest` and are configured through `pyproject.toml` with `src/` on the import path. Add or update tests with every behavioral change. Name test files `test_*.py` and keep them close to the subsystem they cover, such as `tests/fetchers/` or `tests/verification/`. Prefer focused unit tests first, then integration coverage for CLI flows when command wiring changes.

## Commit & Pull Request Guidelines

Recent history uses conventional prefixes such as `feat:`, `fix:`, and `chore:`. Keep commit messages short and imperative, for example `fix: harden github fetching`. Pull requests should explain the user-visible change, note any manifest or workflow impact, link the relevant issue when available, and list the verification commands you ran.

## Security & Configuration Tips

`red_env build` fetches assets from GitHub. Set `GH_TOKEN` or `GITHUB_TOKEN` locally to avoid API rate limits, but never commit tokens or other secrets. For agent-driven changes, keep edits scoped, preserve existing repo conventions, and finish by re-running `python -m pytest -q`.
