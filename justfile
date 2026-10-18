# List available recipes.
default:
    @just --list

# Run all repository linters.
lint: lint-gh-action lint-markdown lint-nix lint-yaml

# Lint GitHub Actions workflows.
lint-gh-action:
    @actionlint .github/workflows/*.yml

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
