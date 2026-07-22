# GearMeshing-AI

GearMeshing-AI turns an approved work specification into a reviewable software
change while preserving explicit human authority, provider boundaries, and
auditable execution evidence.

The application version remains `0.0.0` while the governed work-loop proof of
concept is under development.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

## Development Setup

Install the locked development environment from a clean checkout:

```bash
uv sync --locked
```

Inspect the CLI:

```bash
uv run gearmeshing-ai --help
```

## Package Boundaries

The repository is a modular monolith. New work belongs in one of these
top-level packages:

- `gearmeshing_ai/domain`: framework-independent business rules.
- `gearmeshing_ai/application`: use cases and provider-neutral ports.
- `gearmeshing_ai/adapters`: external provider implementations.
- `gearmeshing_ai/runtime`: process composition and lifecycle support.
- `gearmeshing_ai/interfaces`: CLI, HTTP, and event-facing interfaces.

Existing packages remain available while the rewrite is migrated incrementally.
Do not introduce a service split or a separate SaaS UI in the POC foundation.

## Verification

Run the unit suite:

```bash
uv run pytest test/unit_test
```

Run formatting and lint checks:

```bash
uv run ruff format --check gearmeshing_ai test
uv run ruff check gearmeshing_ai test
```

Run static type checks:

```bash
uv run mypy gearmeshing_ai
```

Run all test groups when validating a cross-boundary change:

```bash
uv run pytest test/unit_test test/integration_test test/contract_test
```

## Delivery

All changes are developed in ticket-specific worktrees and delivered through
Draft pull requests targeting `main`. Never commit credentials or generated
runtime data.

## License

[MIT License](./LICENSE)
