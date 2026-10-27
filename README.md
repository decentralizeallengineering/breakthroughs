# breakthroughs

Cheap models brainstorm wildly about a project, then one stronger model checks each idea for reliability.

## Why

A single careful agent tends to propose safe, similar ideas. Several cheap agents, each forced through a different lens and told not to censor themselves, find odd ideas that a careful agent would never write down. A reviewer then scores which ones are cheap, reversible and likely to work, so wild ideas are not trusted blindly.

## Install

Requires Python 3.9+ and the `claude` command line tool. No other dependencies.

    git clone <this repo> && cd breakthroughs
    ln -s "$PWD/bin/breakthroughs" ~/.local/bin/breakthroughs

Set `BREAKTHROUGHS_PROMPTS` to use another prompts directory (default: `prompts/` next to `bin/`).

## Configure

- `prompts/lenses.md`: one lens per line (`- name: instruction`). Workers get distinct lenses in file order. Keep at least 10.
- `prompts/hot.md`: the brainstorm prompt, which asks for quantity and boldness and forbids self-censoring on feasibility.
- `prompts/cool.md`: the review prompt.

The number of workers is clamped to 3..10 in code. Both phases run `claude -p` with only the Read, Grep and Glob tools, with the target repository as the working directory.

## Use

    breakthroughs run ~/src/myproject --goal "Halve the time to ship a release" --workers 6
    breakthroughs run ~/src/myproject --goal "..." --dry-run     # print the commands, call no model
    breakthroughs report breakthroughs/ideas.jsonl               # re-render the report

Options: `--hot-model haiku`, `--judge-model sonnet`, `--out DIR` (default `./breakthroughs`), `--timeout SECONDS`.

Output goes to `breakthroughs/report-<date>.md` and `breakthroughs/ideas.jsonl`. Near-identical ideas are merged by token Jaccard similarity, and each idea records how many different lenses found it. The judge gives each idea a works score (0-5), the repository evidence it checked, the reliability risk, the cost to try in hours and the reversibility, and ranks it as TRY NOW, SPIKE or PARK. A worker line that is not valid JSON is recorded as a parse failure in both files. Content is never repaired or guessed.

## The same pattern as a Claude Code subagent recipe

Without this tool, ask the parent session for the same two phases:

    Spawn N subagents (3 to 10) with model haiku and tools Read, Grep, Glob only, in parallel.
    Give each a different lens from prompts/lenses.md and the text of prompts/hot.md with my goal.
    Each must reply with JSON lines {idea, why_it_could_work, first_step, evidence_in_repo}
    and must not censor ideas on feasibility.
    Merge near-duplicate ideas yourself and note how many lenses found each.
    Then spawn ONE subagent with model sonnet and tools Read, Grep, Glob, using prompts/cool.md and the
    merged list. It scores each idea (works 0-5 with evidence checked, reliability risk, cost in hours,
    reversibility) and returns a ranked list: TRY NOW, SPIKE, PARK.
    Report any subagent reply that is not valid JSON as a failure instead of guessing its content.

## Test

    python3 -m unittest discover -s tests

## License

Apache-2.0. See LICENSE and NOTICE.
