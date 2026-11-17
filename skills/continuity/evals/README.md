# Continuity evaluations

These evaluations inspect filesystem effects, not only the agent's final response.
Each case starts from synthetic files under `fixtures/` and runs twice: once with
the skill and once without it as a baseline.

| Case | Observable behavior |
| --- | --- |
| `preserve-contradictions` | Keeps conflicting evidence, excludes private details, and configures the declared agent-wide startup mechanism. |
| `forget-across-records` | Removes requested traces from summaries, facets, journey entries, retained copies, and links without deleting unrelated material. |
| `project-only-capability` | Uses the only authorized project scope and reports that agent-wide continuity remains partial. |

## Run

Enter the Nix development shell, authenticate the Codex CLI, then run:

```sh
just eval-continuity
```

The recipe uses ephemeral Codex sessions, ignores user configuration and project
rules, and limits writes to each copied fixture workspace. It runs six task
sessions—three with the skill and three baselines—plus two isolated semantic
reviews for the contradiction case.

To validate the manifest and fixture inventory and run deterministic runner
regressions without calling a model:

```sh
just lint-evals
```

## Results

Each run remains under `results/<timestamp>/`, which Git ignores because traces
can be large or sensitive. `run.json` records the command, agent version,
platform, and hashes of the skill sources used.

Each case and mode retains:

- `workspace/`: the final files;
- `changes.json`: files added, modified, and removed;
- `grading.json`: every deterministic and semantic assertion with its evidence;
- `trace.jsonl`: the complete task-agent event stream;
- `final-response.txt` and `stderr.log`;
- `prompt.txt`: the exact skill, task, and evaluation contract presented;
- `semantic-*.jsonl`, `semantic-*.txt`, and `semantic-grading.json` when the
  case requires a separate semantic review.

The contradiction case mechanically requires modified summaries, a substantive
new journey entry, links to that entry, the new lesson, and explicit uncertainty.
A separate ephemeral reviewer then compares the initial and final files against
two documented semantic rubrics. It must cite paths and quotes; it never grades
the task agent's final response or `eval-report.json`.

The run-level `benchmark.json` compares assertion and case pass rates. A run
fails when any with-skill case fails; baseline failures are measurements, not
runner failures. Review `workspace/`, `changes.json`, and `trace.jsonl` when a
score hides an incorrect side effect.
