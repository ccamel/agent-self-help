# List available recipes.
default:
    @just --list

# Apply available automatic fixes, then run all linters.
fix: fix-just fix-markdown fix-nix
    @just lint

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
lint: lint-gh-action lint-just lint-markdown lint-nix lint-skills lint-yaml

# Lint GitHub Actions workflows.
lint-gh-action:
    @actionlint .github/workflows/*.yml

# Check Just file formatting.
lint-just:
    @just --fmt --check

# Validate Agent Skills.
lint-skills:
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
