# Copilot instructions for kai-dc-builder

## Project overview

- This repo is the public documentation source for KAI Data Center Builder. Primary content lives under docs/ with site structure defined in mkdocs.yml (Material for MkDocs).
- Styles live in stylesheets/ (e.g., stylesheets/extra.css) and are referenced from mkdocs.yml.
- Public artifacts and end-user config examples live under aidc/ (e.g., aidc/compose.yml). Versioned values and download URLs are centralized in aidc/env.latest.
- Internal-only docs and scripts are in REALLY_README.md and ci-scripts/; these are excluded from public publishing.
- The project uses GitHub Actions for CI; see .github/workflows/ for workflow definitions.
- The project builds a public docker image for the kai-specific ingress controller and tests it.

## Build and preview workflow

- Local docs build uses MkDocs with requirements in requirements.txt (mkdocs-material, pymdown-extensions).
- The project builds a public docker image for the kai-specific ingress controller and tests it.

## Publishing pipeline (Copybara)

- CI publishes to the public GitHub repo using Copybara; see ci-scripts/README.md and ci-scripts/Makefile.
- The pipeline creates a temporary commit with docs changes, runs copybara, then resets the commit. Internal files in ci-scripts/, copybara/, or .gitlab-ci.yml are intentionally excluded.
- If you add new public files, ensure they are covered by the origin_files globs in ci-scripts/copy.bara.sky (docs/, README.md, mkdocs.yml, aidc/, .github/).

## Content conventions

- Keep public docs free of proprietary/internal-only info (see REALLY_README.md for the internal/public split).
- Only humans are allowed to modify README.md.
- Update mkdocs.yml nav when adding docs pages so they appear in the rendered site.
- Prefer editing Markdown under docs/ instead of embedding large content in README.md.

## Helpful references

- Documentation entry points: docs/index.md, docs/solution/intro.md, docs/deployment/overview.md.
- Release/version info: aidc/env.latest and docs/kaidcb/versions.md.
