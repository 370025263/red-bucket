# Contributing to red-bucket

Thank you for contributing to `red-bucket`! The official public origin is https://redbucket.store, and local development or self-hosted deployments use `RED_BUCKET_URL`. Please follow these guidelines when submitting changes.

---

## Environment & Prerequisites

- **Python:** `3.12` (managed via `uv`)
- **System Git:** `>= 2.40`
- **Dependencies:** Install using `uv sync`

---

## Quality Gates

Before submitting a pull request or merging any changes, ensure all quality gates pass:

```bash
# Run the complete lint gate (Semgrep, Ruff PEP8 E/W, Pylint naming, Vulture dead-code)
make lint

# Run the test suite
make test
```

For offline development without internet access, run:

```bash
make lint-custom
```

---

## The Three-Name Rule

To prevent conceptual ambiguity across tools, APIs, and client agents, three distinct operations must never be mixed or aliased in code, documentation, or tests:

1. **`copy`** (`POST /api/v1/users/{username}/buckets/{bucket}/copies`): Copies an asset between buckets with provenance history. Returns an `InstallRecord` JSON object.
2. **`install-script`** (`GET /api/v1/users/{username}/buckets/{bucket}/install-script`): Generates a portable shell script that downloads and unpacks translated assets onto the local filesystem.
3. **`translated fetch`** (`GET .../translated`): Streams raw translated bytes or a zip archive transformed on the fly for a specified target harness (`?target=...`).

There is no `POST /install` endpoint.

---

## License

By contributing to `red-bucket`, you agree that your contributions will be licensed under the [MIT License](LICENSE).
