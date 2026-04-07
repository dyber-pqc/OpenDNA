# Contributing to OpenDNA

Thanks for your interest! OpenDNA is community-driven. Here's how to help.

## Ways to contribute

- **Report bugs** — open an issue with reproduction steps
- **Request features** — open an issue describing the use case
- **Improve documentation** — typos, clarifications, new tutorials
- **Add tests** — coverage on engines is the highest-impact contribution
- **Build features** — pick something from the roadmap or propose your own
- **Share workflows** — submit example pipelines to the cookbook
- **Validate science** — run benchmarks and report results

## Quick start for developers

```bash
git clone https://github.com/dyber-pqc/OpenDNA.git
cd OpenDNA

# Python deps
pip install -e ".[dev]"

# UI deps
cd ui && npm install && cd ..

# Run tests
python -m pytest tests/python/ -v
cd ui && npx tsc --noEmit && cd ..

# Run the server
opendna serve
```

See [docs/DEVELOPER.md](docs/DEVELOPER.md) for the full developer guide.

## Code conventions

- **Python**: ruff for linting/formatting, type hints required, docstrings on public APIs
- **TypeScript**: strict mode, functional components, hooks
- **Rust**: rustfmt, no clippy warnings
- **CSS**: use CSS variables from `App.css`, no inline styles
- **Commit messages**: follow Conventional Commits — `feat:`, `fix:`, `docs:`, `refactor:`, etc.

## Pull request process

1. Fork the repo and create a branch from `main`
2. Make your changes with clear commits
3. Add tests for new functionality
4. Run the test suite and make sure it passes
5. Update documentation if user-facing
6. Open a PR with a clear description
7. Wait for CI to pass
8. Address review feedback
9. Maintainer merges

## Things we will NOT accept

- Code without tests for new functionality
- Breaking changes without discussion
- Proprietary code we can't relicense
- Vendoring of large binaries
- Changes that break cross-platform support
- Anything with hardcoded secrets
- AI-generated code without verification (we love AI tools, but you must read and verify the output)

## Code of Conduct

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## License

By contributing, you agree to license your contributions under the same terms as the project (Apache 2.0 + Commons Clause).

## Questions?

- Open a GitHub Discussion
- File an issue with the `question` label
- Join our Discord (link coming soon)
