//! Sans-IO lifecycle decisions. This module owns no paths, processes, locks, or
//! heap buffers; callers interpret the returned effect through pipes.

/// Current lifecycle phase for one virtual environment.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    Absent,
    Creating,
    CreatingEphemeral,
    Ready,
    Entering,
    EnteringEphemeral,
    Active,
    ActiveEphemeral,
    Removing,
    CleaningEphemeralFailure,
    Failed,
}

/// A requested operation or an observation from the effect runner.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Event {
    Create,
    CreateEphemeral,
    Enter,
    Remove,
    Created,
    Entered,
    Exited,
    Removed,
    Failed,
}

/// Effect for the caller to execute. `Rejected` is a pure decision, not I/O.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Effect {
    None,
    Create,
    Enter,
    Remove,
    Rejected,
}

/// Apply one event without performing I/O or allocating.
///
/// The tuple is intentionally the entire transition result; a wrapper struct
/// would add a type without carrying additional invariants or behavior.
#[must_use]
pub const fn transition(state: State, event: Event) -> (State, Effect) {
    match (state, event) {
        (State::Absent, Event::Create) => (State::Creating, Effect::Create),
        (State::Absent, Event::CreateEphemeral) => (State::CreatingEphemeral, Effect::Create),
        (State::Absent, Event::Enter) => (State::Entering, Effect::Enter),
        (State::Absent, Event::Remove) => (State::Removing, Effect::Remove),
        (State::Creating, Event::Created) => (State::Ready, Effect::None),
        (State::CreatingEphemeral, Event::Created) => (State::EnteringEphemeral, Effect::Enter),
        (State::Entering, Event::Entered) => (State::Active, Effect::None),
        (State::EnteringEphemeral, Event::Entered) => (State::ActiveEphemeral, Effect::None),
        (State::Ready, Event::Enter) => (State::Entering, Effect::Enter),
        (State::Ready, Event::Remove) => (State::Removing, Effect::Remove),
        (State::Active, Event::Exited) => (State::Ready, Effect::None),
        (State::Active, Event::Remove) => (State::Removing, Effect::Remove),
        (State::ActiveEphemeral, Event::Exited) => (State::Removing, Effect::Remove),
        (State::Removing, Event::Removed) => (State::Absent, Effect::None),
        (State::Creating | State::Entering, Event::Failed) => (State::Failed, Effect::None),
        (
            State::CreatingEphemeral | State::EnteringEphemeral | State::ActiveEphemeral,
            Event::Failed,
        ) => (State::CleaningEphemeralFailure, Effect::Remove),
        (State::CleaningEphemeralFailure, Event::Removed) => (State::Failed, Effect::None),
        (State::Failed, Event::Remove) => (State::Removing, Effect::Remove),
        (State::Removing, Event::Failed) => (State::Failed, Effect::None),
        (State::Failed, Event::Removed) => (State::Absent, Effect::None),
        (state, _) => (state, Effect::Rejected),
    }
}

#[cfg(test)]
mod tests {
    use super::{Effect, Event, State, transition};

    const STATES: [State; 11] = [
        State::Absent,
        State::Creating,
        State::CreatingEphemeral,
        State::Ready,
        State::Entering,
        State::EnteringEphemeral,
        State::Active,
        State::ActiveEphemeral,
        State::Removing,
        State::CleaningEphemeralFailure,
        State::Failed,
    ];
    const EVENTS: [Event; 9] = [
        Event::Create,
        Event::CreateEphemeral,
        Event::Enter,
        Event::Remove,
        Event::Created,
        Event::Entered,
        Event::Exited,
        Event::Removed,
        Event::Failed,
    ];

    const EXPECTED: [((State, Event), (State, Effect)); 23] = [
        (
            (State::Absent, Event::Create),
            (State::Creating, Effect::Create),
        ),
        (
            (State::Absent, Event::CreateEphemeral),
            (State::CreatingEphemeral, Effect::Create),
        ),
        (
            (State::Absent, Event::Enter),
            (State::Entering, Effect::Enter),
        ),
        (
            (State::Absent, Event::Remove),
            (State::Removing, Effect::Remove),
        ),
        (
            (State::Creating, Event::Created),
            (State::Ready, Effect::None),
        ),
        (
            (State::Creating, Event::Failed),
            (State::Failed, Effect::None),
        ),
        (
            (State::CreatingEphemeral, Event::Created),
            (State::EnteringEphemeral, Effect::Enter),
        ),
        (
            (State::CreatingEphemeral, Event::Failed),
            (State::CleaningEphemeralFailure, Effect::Remove),
        ),
        (
            (State::Entering, Event::Entered),
            (State::Active, Effect::None),
        ),
        (
            (State::Entering, Event::Failed),
            (State::Failed, Effect::None),
        ),
        (
            (State::EnteringEphemeral, Event::Entered),
            (State::ActiveEphemeral, Effect::None),
        ),
        (
            (State::EnteringEphemeral, Event::Failed),
            (State::CleaningEphemeralFailure, Effect::Remove),
        ),
        (
            (State::Ready, Event::Enter),
            (State::Entering, Effect::Enter),
        ),
        (
            (State::Ready, Event::Remove),
            (State::Removing, Effect::Remove),
        ),
        ((State::Active, Event::Exited), (State::Ready, Effect::None)),
        (
            (State::Active, Event::Remove),
            (State::Removing, Effect::Remove),
        ),
        (
            (State::ActiveEphemeral, Event::Exited),
            (State::Removing, Effect::Remove),
        ),
        (
            (State::ActiveEphemeral, Event::Failed),
            (State::CleaningEphemeralFailure, Effect::Remove),
        ),
        (
            (State::Removing, Event::Removed),
            (State::Absent, Effect::None),
        ),
        (
            (State::Removing, Event::Failed),
            (State::Failed, Effect::None),
        ),
        (
            (State::CleaningEphemeralFailure, Event::Removed),
            (State::Failed, Effect::None),
        ),
        (
            (State::Failed, Event::Remove),
            (State::Removing, Effect::Remove),
        ),
        (
            (State::Failed, Event::Removed),
            (State::Absent, Effect::None),
        ),
    ];

    #[test]
    fn lifecycle_paths_and_all_pairs_are_defined_without_heap_state() {
        let mut state = State::Absent;
        let (next, effect) = transition(state, Event::CreateEphemeral);
        assert_eq!((next, effect), (State::CreatingEphemeral, Effect::Create));
        state = next;
        let (next, effect) = transition(state, Event::Created);
        assert_eq!((next, effect), (State::EnteringEphemeral, Effect::Enter));
        state = next;
        let (next, effect) = transition(state, Event::Entered);
        assert_eq!((next, effect), (State::ActiveEphemeral, Effect::None));
        state = next;
        assert_eq!(
            transition(state, Event::Exited),
            (State::Removing, Effect::Remove)
        );

        assert_eq!(
            transition(State::EnteringEphemeral, Event::Failed),
            (State::CleaningEphemeralFailure, Effect::Remove)
        );
        assert_eq!(
            transition(State::CleaningEphemeralFailure, Event::Removed),
            (State::Failed, Effect::None)
        );

        for state in STATES {
            for event in EVENTS {
                let actual = transition(state, event);
                let expected = EXPECTED
                    .iter()
                    .find(|(pair, _)| *pair == (state, event))
                    .map_or((state, Effect::Rejected), |(_, result)| *result);
                assert_eq!(actual, expected, "transition for {state:?} + {event:?}");
            }
        }

        for _ in 0..10_000 {
            let mut state = State::Absent;
            for event in [
                Event::CreateEphemeral,
                Event::Created,
                Event::Entered,
                Event::Exited,
                Event::Removed,
            ] {
                state = transition(state, event).0;
            }
            assert_eq!(state, State::Absent);
        }
    }
}
