# Migration plan

Each estimate is an assumed wall-clock budget for implementation, checks, two
reviews, postmortem, commit, and worktree → local `main` → `origin/main` landing.
The limit is 20 minutes per card. Split a card if its observed work exceeds the
limit; do not land a red checkpoint. Local total: **585 minutes (9h 45m)**,
revised from observed card duration after each landing. Remote CI and package
index queues can add unknown external wait.

| Card | Deliverable and acceptance | Depends on | Estimate |
|---|---|---|---:|
| C01 | Timestamped ledger, ordered plan, gate that runs/logs a command and rejects failures or zero tests. `python scripts/card_gate.py --self-test`; run nine gate unit tests. | — | 15m |
| C02 | Pin Proxima ref; read Pipe and all combinators; record verdict per combinator and test one actual pipe composition in an isolated proof crate. `cargo test --manifest-path docs/cards/proxima-pipe-proof/Cargo.toml` reports N>0 against the pinned source; audit has source refs. | C01 | 18m |
| C03 | Rust workspace plus runtime `Config` using `#[derive(Settings)]`; central env/fluent paths explicitly `.validate()`; preserve Python until Rust config parity. Invalid empty name rejected. `cargo test -p vsh-core config` (N>0). | C02 | 18m |
| C04 | `CreateOptions`/`EnterOptions` derive Settings+Validate; one default source, env/serde/fluent parity including pip and platform symlinks. `cargo test -p vsh-core options` (N>0). | C03 | 17m |
| C05 | Sans-IO lifecycle FSM with exhaustive transitions/effects and no allocation in repeated transition test. `cargo test -p vsh-core lifecycle` (N>0). | C03-C04 | 18m |
| C06 | Proxima pipe shape compiled for lifecycle effects; document `In`/`Out`/`Err`, justify new types. `cargo test -p vsh-core pipe_shape` (N>0). | C02,C05 | 18m |
| C07 | Generate walk-depth build constant through conflaguration with one source of truth. Env override build check and `cargo test -p vsh-core limits` (N>0). | C03 | 15m |
| C08 | Validated legacy TOML load/store routed through pipe effect seam. Legacy fixtures and invalid input. `cargo test -p vsh-core config_file` (N>0). | C06 | 18m |
| C09 | Venv layout observation/validation behind a pipe. `cargo test -p vsh-core venv_layout` (N>0). | C06 | 17m |
| C10 | Create effect pipe using validated options. Real temp venv create test. `cargo test -p vsh-core create_venv` (N>0). | C06,C09 | 18m |
| C11 | Remove effect pipe, guard, config cleanup, dry-run semantics. `cargo test -p vsh-core remove_venv` (N>0). | C08-C10 | 17m |
| C12 | Bounded discovery/interpreter/vshrc pipe. Symlink-loop and real interpreter fixture. `cargo test -p vsh-core discovery` (N>0). | C07,C09 | 18m |
| C13 | Shell environment and child execution pipe, exit code and cwd. Real child tests. `cargo test -p vsh-core shell` (N>0). | C06,C12 | 18m |
| C14 | CLI parser/help/list/completion only. `cargo test -p vsh-cli cli` (N>0), plus `vsh --help`. | C13 | 16m |
| C15 | CLI resolves file → env → flags and explicitly validates before effects. Precedence/invalid-config tests. `cargo test -p vsh-cli config` (N>0). | C08,C14 | 18m |
| C16 | CLI drives FSM and composed pipes for create/enter/remove/ephemeral. Real child and cleanup tests. `cargo test -p vsh-cli` (N>0). | C11,C13,C15 | 18m |
| C17 | PyO3 config/options/errors; constructors and loaders validate. Build/import tests. `maturin build` plus Python config tests (N>0). | C15 | 17m |
| C18 | PyO3 Venv API delegates to the same Rust pipes. Installed wheel tests (N>0). | C16,C17 | 18m |
| C19 | Proxima recorder/filter/spans/error reporting; prove records with configured recorder and silence with no-op recorder. `cargo test -p vsh-cli telemetry` (N>0). | C16 | 16m |
| C20 | Measured allocation/copy/lock audit and named Python cold-start benchmark with variance; split if measurement/review exceeds time. `scripts/bench-compare.sh` and recorded artifacts. | C18,C19 | 18m |
| C21 | Native Windows shell semantics and quoting. Native Windows command/exit tests (N>0). | C13,C16 | 18m |
| C22 | Native Windows venv layout/discovery/config/remove. Native create→enter→remove test (N>0). | C21 | 18m |
| C23 | Pip wheel console entry invokes shared Rust CLI; installed wheel exposes CLI and PyO3 API. Temp-env install, `vsh --version`, import tests (N>0). | C16,C18 | 18m |
| C24 | Native macOS/Linux/Windows matrix; each job builds and smoke-tests wheel, CLI, and library with nonzero counts. Inspect completed CI jobs. | C21-C23 | 18m |
| C25 | Proxima Teacher end-user install/configure/use docs and executable examples. Run every native-platform guide command in isolated temp home. | C24 | 39m actual |
| C29 | Preserve child-shell stdout/stderr without trailing newlines through the installed Python console; native installed-wheel regression proves exact bytes. | C23 | 17m actual (16m33s) |
| C26 | Set Cargo, Python, persisted config, examples and changelog to 0.8.0; full green gates and wheel metadata. | C25,C29 | 15m |
| C30 | Retain each green native 0.8.0 wheel as a workflow artifact named with exact source SHA and platform. | C26 | 15m planned |
| C27 | Reconcile the release artifact provenance gate with retained native artifacts; review and split the remaining work into independently green cards. | C26,C30 | 18m |
| C31 | Download exact-SHA native wheels, build same-SHA sdist, verify metadata/platform tags and source inventory, emit and independently recompute a four-file SHA-256 manifest. | C27 | 18m |
| C32 | Re-run source test gate and final collision/hash checks; create and prove the local-only v0.8.0 tag at the C30 candidate SHA. | C31 | 18m |
| C28 | Submit verified artifacts to GitHub release/PyPI and capture accepted receipts. If any upload/review exceeds 20m, split at a safe boundary. | C32 | 15m |

Package-index availability is an external verification milestone after C28,
with an unknown wait; it is not included in the local ETA. Never claim the
published version until the index exposes the exact 0.8.0 artifact/hash.

## Cross-card rules

- Runtime configuration derives `Settings` and each resolved value explicitly
  calls `.validate()` before it reaches the Rust library. The CLI gathers and
  passes config into the library. Conflaguration's `.build()` and
  `from_file_then_env()` do not validate automatically.
- The Proxima audit, pure FSM, and compiled pipe shape precede filesystem,
  process, CLI action, and PyO3 effect implementations. Read the pinned trait,
  every combinator, and each applicable example before coding.
- Prefer existing primitives and justify every new struct. Keep decision logic
  sans-IO; express effects with pipes. Be honest about OS boundaries and memory
  ownership; zero-copy/zero-lock are measured/audited properties, not claims.
- Native platform cards require that platform's green job. A macOS-only check
  does not close a Windows card. Every card gets separate code↔card and
  tests↔card reviews, validation result counts, UTC timestamps and postmortem.
