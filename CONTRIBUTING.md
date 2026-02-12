# Contributing

We welcome contributions! Please follow these guidelines.

## Developer Certificate of Origin (DCO)

All commits **must** include a `Signed-off-by` trailer. This certifies you wrote or have the right to submit the code under the project's license.

Sign your commits with:

```bash
git commit -s -m "Your commit message"
```

This adds a line like:

```
Signed-off-by: Your Name <your.email@example.com>
```

## Getting Started

1. Fork the repository
2. Clone your fork
3. Install dependencies:

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Development Workflow

Use the Makefile for common tasks:

```bash
make lint       # Run ruff linter
make fmt        # Auto-format code
make test       # Run unit tests
make e2e        # Run e2e test against sample image
make check      # Run all checks (lint + test + e2e)
```

## Code Style

- Code is formatted and linted with [Ruff](https://docs.astral.sh/ruff/)
- Line length: 100 characters
- All Python files must include the Apache 2.0 license header

## Tests

- Unit tests live in `tests/` and are run with pytest
- Pure-Python logic should have unit tests (no Tesseract needed)
- E2E tests run against `examples/sample.png`

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes
3. Run `make check` to verify everything passes
4. Submit a PR with a clear description
5. All commits must be signed off (DCO)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
