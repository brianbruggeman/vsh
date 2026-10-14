# vsh Rust migration cards

Each card must land as a green, independently reviewable commit in under 20
minutes, including its checks, both reviews, postmortem, and landing. Work flows
from a card worktree branch to local `main`, then to `origin/main`; promotion is
fast-forward only.

For every card, keep the card text, exact validation commands, result counts,
separate card-to-code and tests-to-card reviews, and a short postmortem here.
Record each start and completion in `progress.jsonl` with a UTC timestamp,
elapsed time, done/todo IDs, and a revised ETA. Never call a card green when a
test selection ran zero tests.

## Card order

The detailed plan and dependencies are in `plan.md`. Runtime conflaguration
cards precede dispatch: every runtime config uses `#[derive(Settings)]`, and
each resolved value is explicitly `.validate()`d before it reaches the library.
The CLI gathers configuration and passes it into the Rust API.

## Progress

See `progress.jsonl` for timestamped status events. Each card note is linked by
its ID (for example, `C01.md`). The initial green baseline
is commit `6d3c237` on `origin/main`: 74 Python tests passed on Python 3.11.10.
The Rust rewrite draft is still uncommitted in the source checkout and is not
part of that baseline.
