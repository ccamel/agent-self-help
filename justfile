# List available recipes.
default:
    @just --list

# Apply available automatic fixes, then run all linters.
fix: fix-catalog fix-just fix-markdown fix-nix
    @just lint

# Generate the README skill catalog from skill frontmatter.
generate-catalog:
    @python scripts/generate-skill-catalog.py

# Fix the README skill catalog by regenerating it.
fix-catalog: generate-catalog

# Run continuity behavioral evals against Codex and a no-skill baseline.
eval-continuity:
    @python scripts/run-skill-evals.py skills/continuity -- codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox workspace-write --color never --json -

# Format the Just file.
fix-just:
    @just --fmt

# Fix Markdown files.
fix-markdown:
    @markdownlint --fix "**/*.md"

# Fix Nix antipatterns and formatting.
fix-nix:
    @statix fix .
    @nixfmt flake.nix

# Run all repository linters.
lint: lint-catalog lint-evals lint-gh-action lint-images lint-just lint-markdown lint-nix lint-skills lint-yaml

# Check that the README skill catalog is current.
lint-catalog:
    @python scripts/generate-skill-catalog.py --check

# Validate eval manifests and fixture inventories without calling a model.
lint-evals:
    @python scripts/run-skill-evals.py skills/continuity --validate
    @python scripts/test-run-skill-evals.py

# Lint GitHub Actions workflows.
lint-gh-action:
    @actionlint .github/workflows/*.yml

# Limit image sizes and disallow PNG.
lint-images:
    @python scripts/lint-images.py

# Check Just file formatting.
lint-just:
    @just --fmt --check

# Check independent skill releases in an isolated local Git repository.
lint-releases:
    @uv run --no-project --with python-semantic-release==10.7.0 --with pyyaml python scripts/test-skill-releases.py

# Validate Agent Skills.
lint-skills: lint-evals lint-releases
    @python scripts/generate-skill-catalog.py --validate
    @for dir in skills/*/; do uvx --from git+https://github.com/agentskills/agentskills.git@69ef37e9424c0a7ea9dd2293b559e43ec8176379#subdirectory=skills-ref skills-ref validate "$dir"; done
    @npx skill-check@1.2.0 check --no-security-scan skills

# Lint Markdown files.
lint-markdown:
    @markdownlint "**/*.md"

# Check the Nix flake, formatting, antipatterns, and dead code.
lint-nix:
    @nix flake check path:. --all-systems
    @nixfmt --check flake.nix
    @statix check .
    @deadnix --fail .

# Lint YAML files.
lint-yaml:
    @yamllint .
