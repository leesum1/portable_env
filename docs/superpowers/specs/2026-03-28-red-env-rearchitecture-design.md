# Red Environment Re-architecture Design

- Date: 2026-03-28
- Status: Approved for planning
- Scope: Phase 1 redesign spec

## Background

The current repository delivers offline installation packages for common Linux terminal tools on `x86_64` and `arm64`, using Docker for packaging and Docker again for verification.

The current implementation has three structural problems:

1. Repository boundaries are unclear. Source code, manifests, temporary outputs, generated artifacts, and historical scratch data coexist in the same top-level structure.
2. Software installation behavior is implicit. The actual installation method for a package is distributed across `Dockerfile`s and scripts instead of being declared in one place.
3. Build orchestration is over-coupled. `docker/Dockerfile.build` currently mixes package acquisition, special-case logic, bundle assembly, and output packaging.

This redesign intentionally prioritizes repository architecture over backward compatibility with the current implementation.

## Goals

Phase 1 must preserve these core capabilities:

1. Build offline packages for `x86_64` and `arm64`.
2. Keep an offline installer flow for end users.
3. Keep a Docker-based verification loop that installs and tests the resulting package in a clean container.

Phase 1 must also introduce these architectural changes:

1. Replace the current package definition model with TOML-based manifests.
2. Make package grouping explicit through build-time profiles: `core`, `extended`, and `experimental`.
3. Make each package declare an explicit installation strategy.
4. Replace the current multi-entry build surface with a single Python CLI.
5. Reduce Docker to an isolated execution environment, not a source of business rules.

## Non-goals

Phase 1 explicitly does not do the following:

1. Preserve compatibility with the current `Makefile`-first interface.
2. Preserve `release_files/packages.json` or its current data model.
3. Support source compilation as a fallback for packages that do not provide stable prebuilt assets.
4. Retain scattered package-specific special handling inside Dockerfiles.
5. Migrate every currently shipped package regardless of fit.

If a package cannot be expressed cleanly with the supported manifest schema and supported installation strategies, it is excluded from Phase 1.

## Design Principles

The redesign follows these principles:

1. Single source of truth. Package and profile rules live in manifests, not in Dockerfiles or ad hoc scripts.
2. Explicit strategy modeling. Each package must declare how it is acquired and how its files enter the offline bundle.
3. Clear boundaries. Manifest parsing, fetching, bundle assembly, installer generation, and verification are separate concerns.
4. Build-time profile selection. Profiles are chosen by maintainers when building packages, not by end users at install time.
5. No source builds in Phase 1. The framework stays constrained to stable prebuilt assets.

## Target Repository Layout

The repository should be reorganized around source code, manifests, static assets, Docker runtime definitions, generated outputs, and tests.

```text
red_env/
├── src/red_env/
│   ├── cli/
│   ├── manifest/
│   ├── fetchers/
│   ├── strategies/
│   ├── packaging/
│   ├── installer/
│   └── verification/
├── manifests/
│   ├── manifest.toml
│   ├── profiles.toml
│   ├── bundle.toml
│   └── packages/
│       ├── fzf.toml
│       ├── bat.toml
│       ├── zsh.toml
│       └── tmux.toml
├── docker/
│   ├── builder.Dockerfile
│   └── verifier.Dockerfile
├── assets/
│   ├── configs/
│   └── installer/
├── build/
├── dist/
├── tests/
└── docs/
```

### Directory responsibilities

- `src/red_env/` contains the Python CLI and all execution logic.
- `manifests/` contains the only supported configuration surface for package definition and profile composition.
- `docker/` contains isolated runtime definitions for building and verification only.
- `assets/` contains static files bundled into the offline package, such as shell configs and installer templates.
- `build/` is the working directory for temporary and intermediate outputs. It is generated and ignored.
- `dist/` contains final deliverables such as tarballs and checksums. It is generated and ignored.
- `tests/` contains unit, integration, and end-to-end verification coverage.

Top-level directories such as `tmp/`, `output_x86_64/`, and `output_arm64/` are removed from the architecture and replaced by deterministic paths under `build/`.

## Manifest Architecture

The new system is manifest-driven, but the manifest is split into focused TOML files instead of one oversized document.

### Manifest entrypoint

`manifests/manifest.toml` is the root entrypoint. It declares manifest versioning and the set of files that compose the full configuration model.

### Profile definition

`manifests/profiles.toml` defines the supported build-time profiles:

- `core`
- `extended`
- `experimental`

Profiles may inherit from each other. For example, `extended` may include everything in `core` plus additional packages.

### Bundle definition

`manifests/bundle.toml` defines the target layout of the offline bundle, including canonical directories such as:

- `bin/`
- `share/`
- `configs/`
- `cache/`
- `fonts/`

This file centralizes bundle layout decisions so those paths do not become hard-coded across build logic.

### Package definitions

Each package is defined in its own file under `manifests/packages/`.

Example:

```toml
id = "fzf"
description = "fzf fuzzy finder"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "github_release"
repo = "junegunn/fzf"

[strategy]
type = "archive_extract"

[strategy.match]
x86_64 = '(?i).*linux.*amd64.*tar.gz$'
arm64 = '(?i).*linux.*arm64.*tar.gz$'

[strategy.extract]
include = ["fzf"]
target_dir = "bin"
```

Each package file must declare:

1. Stable package identity.
2. Target profiles.
3. Supported architectures.
4. Source definition.
5. Installation strategy.

## Supported Package Model

Phase 1 supports a constrained acquisition and installation model.

### Supported source types

Phase 1 only needs one source type:

- `github_release`

The design leaves room for future source expansion, but no additional source types are required in this phase.

### Supported strategy types

Phase 1 supports only a small set of explicit installation strategies:

1. `direct_binary`
2. `archive_extract`
3. `directory_copy`

These strategy names describe how fetched assets are transformed into bundle contents.

### Unsupported strategies

The following are intentionally excluded from Phase 1:

1. `build_from_source`
2. Dockerfile-only special cases with no manifest representation
3. Package-specific imperative logic that cannot be described through the manifest schema

This restriction is intentional. It prevents the new framework from inheriting the same ambiguity that exists in the current repository.

## Python Execution Architecture

The new primary interface is a Python CLI under `src/red_env/`.

### Module boundaries

- `cli/` exposes the user-facing commands.
- `manifest/` loads, merges, validates, and resolves TOML definitions.
- `fetchers/` retrieves assets from declared sources.
- `strategies/` applies package-specific installation strategies to fetched assets.
- `packaging/` assembles bundle directories and creates release artifacts.
- `installer/` injects installer resources and bundle metadata.
- `verification/` drives Docker-based installation and validation.

Each module has a single responsibility. In particular:

- `manifest/` validates structure but does not download anything.
- `fetchers/` retrieves artifacts but does not decide bundle layout.
- `strategies/` transforms retrieved files into bundle contents but does not package tarballs.
- `verification/` consumes final artifacts and does not reinterpret build rules.

## CLI Surface

The repository should expose one coherent command surface.

Recommended commands:

```bash
python -m red_env manifest lint
python -m red_env profile show core
python -m red_env build --profile core --arch x86_64
python -m red_env build --profile extended --arch arm64
python -m red_env verify --profile core --arch x86_64
python -m red_env release --profile core --arch x86_64
```

### Command responsibilities

- `manifest lint`
  Validates all TOML inputs, schema rules, profile references, package references, and strategy fields before build starts.

- `profile show`
  Resolves a profile and prints the final package set for inspection.

- `build`
  Resolves `profile + arch`, downloads assets, applies strategies, assembles the bundle tree, injects static assets, and emits a release artifact plus checksum.

- `verify`
  Installs the generated package inside the verifier container and runs validation checks.

- `release`
  Produces the standardized deliverable set from a successful build without redefining build logic.

## Build and Verification Data Flow

The intended data flow is linear and stage-oriented:

```text
TOML manifests
  -> manifest loader
  -> profile resolver
  -> source fetcher
  -> strategy executor
  -> staged bundle directory
  -> packaged artifact
  -> Docker verification
```

Every stage should emit deterministic filesystem outputs under `build/`, for example:

- `build/work/<profile>/<arch>/downloads/`
- `build/work/<profile>/<arch>/bundle/`
- `build/logs/<profile>/<arch>/`
- `dist/<artifact>.tar.gz`

This is important for observability and for debugging package-level failures without reading Dockerfile internals.

## Docker Responsibilities

Docker remains part of the system, but only as infrastructure.

### Builder container

The builder container provides a reproducible runtime for:

1. Running the Python CLI.
2. Downloading package assets.
3. Assembling offline bundle contents.
4. Producing final artifacts.

It must not contain package-specific business rules that are absent from manifests.

### Verifier container

The verifier container provides a clean target environment for:

1. Extracting the package.
2. Running the offline installer.
3. Verifying that key commands work after installation.

It validates the resulting artifact, not the manifest model.

## Error Handling and Observability

The new architecture must fail by stage, not as one undifferentiated build error.

### Manifest errors

Examples:

- Unknown package reference in a profile.
- Missing required package fields.
- Unsupported strategy type.
- Invalid architecture declaration.

These fail in `manifest lint` and block the build before any download starts.

### Fetch errors

Fetch failures must identify:

1. Package id
2. Profile
3. Architecture
4. Source type
5. Source parameters
6. Match rule being used

### Packaging and verification errors

Bundle assembly and Docker verification failures must identify the failed stage directly, for example missing bundle files, installer resource omissions, or command verification failures.

### Logging

Each build should generate structured logs under `build/logs/<profile>/<arch>/`, including package-level logs and a summary of:

1. Successful packages
2. Failed packages
3. Skipped packages
4. Artifact output paths

Intermediate outputs should remain on disk unless explicitly cleaned.

## Testing Strategy

Phase 1 testing should cover four levels:

1. Manifest tests
   Validate TOML loading, merge behavior, profile expansion, and schema constraints.

2. Strategy tests
   Validate each supported strategy against representative asset layouts.

3. CLI integration tests
   Validate command behavior such as `manifest lint`, `profile show`, and build orchestration with mocked downloads.

4. Docker end-to-end verification tests
   Validate that final packages install correctly and expose expected commands in a clean environment.

The first phase should favor correctness, diagnostics, and isolation over advanced features such as shared remote caching, aggressive concurrency, or elaborate retry policies.

## Migration Plan

The migration should build the new system first and only then move packages into it.

Recommended order:

1. Create the new repository layout and CLI skeleton.
2. Implement manifest loading and validation.
3. Implement the supported strategy set.
4. Build a minimal `core` profile and verify it end to end.
5. Migrate additional packages into `manifests/packages/` in batches.
6. Run Docker verification after each migration batch.
7. Remove obsolete entrypoints and the old manifest model after the new path is proven.

This avoids a long-lived half-migrated state where old and new execution models both remain authoritative.

## Final Architectural Decision

Phase 1 will rebuild the project as a TOML-driven, profile-based offline packaging system.

- TOML manifests become the only configuration surface.
- Python becomes the single execution layer.
- Docker becomes isolated infrastructure for build and verification.
- Every package must declare an explicit source and installation strategy.
- Only stable prebuilt assets are supported in this phase.

This design intentionally trades migration breadth for architectural clarity.
