//! Pipe-shaped parsing and static CLI surface for vsh.

mod application;
mod cli_config;
mod run;
mod telemetry;

use std::ffi::OsString;

use proxima_primitives::pipe::Pipe;

pub use application::run_args;
pub use cli_config::{ParseConfigFlagsPipe, ResolveConfigPipe};
pub use run::{ParseCreateOptionsPipe, RunActionPipe};
pub use telemetry::{DrainTelemetryPipe, InstallTelemetryPipe, ResolveTelemetryConfigPipe};

/// One selected top-level command. The enum makes the mutually exclusive
/// command choice explicit while retaining command arguments as OS strings.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CliAction {
    Help,
    Version,
    List(Vec<OsString>),
    Completion(OsString),
    Create(Vec<OsString>),
    Enter(Vec<OsString>),
    Remove(Vec<OsString>),
}

#[cfg(test)]
pub(crate) fn ready<F: core::future::Future>(future: F) -> F::Output {
    use core::task::{Context, Poll, Waker};

    let mut context = Context::from_waker(Waker::noop());
    let mut future = core::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => panic!("CLI configuration pipe must be immediately ready"),
    }
}

/// Parse arguments excluding argv[0].
#[derive(Debug, Clone, Copy, Default)]
pub struct ParseArgsPipe;

impl Pipe for ParseArgsPipe {
    type In = Vec<OsString>;
    type Out = CliAction;
    type Err = String;

    fn call(
        &self,
        mut arguments: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            if arguments.is_empty() {
                return Ok(CliAction::Help);
            }
            let command = arguments.remove(0);
            match command.to_str() {
                Some("--help" | "-h" | "help") => Ok(CliAction::Help),
                Some("--version" | "-V") => Ok(CliAction::Version),
                Some("list") => Ok(CliAction::List(arguments)),
                Some("completion") => Ok(CliAction::Completion(
                    arguments.into_iter().next().unwrap_or_default(),
                )),
                Some("create") => Ok(CliAction::Create(arguments)),
                Some("enter") => Ok(CliAction::Enter(arguments)),
                Some("remove") => Ok(CliAction::Remove(arguments)),
                Some(other) => Err(format!("unknown command: {other}")),
                None => Err("command name is not valid Unicode".to_owned()),
            }
        }
    }
}

/// Return static usage text.
#[derive(Debug, Clone, Copy, Default)]
pub struct HelpPipe;

impl Pipe for HelpPipe {
    type In = ();
    type Out = &'static str;
    type Err = core::convert::Infallible;

    fn call(
        &self,
        (): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async {
            Ok(
                "vsh 0.8.0\n\nUsage: vsh <COMMAND>\n\nCommands:\n  create      Create a virtual environment\n  enter       Enter a virtual environment\n  remove      Remove a virtual environment\n  list        List discovered environments\n  completion  Print command completions\n  help        Print this message\n  --version   Print version\n",
            )
        }
    }
}

/// List supported top-level command names.
#[derive(Debug, Clone, Copy, Default)]
pub struct ListCommandsPipe;

impl Pipe for ListCommandsPipe {
    type In = ();
    type Out = Vec<&'static str>;
    type Err = core::convert::Infallible;

    fn call(
        &self,
        (): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async {
            Ok(vec![
                "create",
                "enter",
                "remove",
                "list",
                "completion",
                "help",
            ])
        }
    }
}

/// Complete top-level names by a caller-supplied prefix.
#[derive(Debug, Clone, Copy, Default)]
pub struct CompleteCommandsPipe;

impl Pipe for CompleteCommandsPipe {
    type In = OsString;
    type Out = Vec<&'static str>;
    type Err = core::convert::Infallible;

    fn call(
        &self,
        prefix: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let prefix = prefix.to_string_lossy();
            Ok(["create", "enter", "remove", "list", "completion", "help"]
                .into_iter()
                .filter(|command| command.starts_with(prefix.as_ref()))
                .collect())
        }
    }
}

#[cfg(test)]
mod tests {
    use core::future::Future;
    use core::task::{Context, Poll, Waker};
    use std::ffi::OsString;

    use proxima_primitives::pipe::Pipe;

    use super::{CliAction, CompleteCommandsPipe, HelpPipe, ListCommandsPipe, ParseArgsPipe};

    fn ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("CLI surface pipes complete in one poll"),
        }
    }

    #[test]
    fn cli_parser_recognizes_commands_and_preserves_os_arguments() {
        assert_eq!(
            ready(ParseArgsPipe.call(Vec::new())).unwrap(),
            CliAction::Help
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["list".into()])).unwrap(),
            CliAction::List(Vec::new())
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec![
                "create".into(),
                OsString::from("--name"),
                OsString::from("demo")
            ]))
            .unwrap(),
            CliAction::Create(vec!["--name".into(), "demo".into()])
        );
        #[cfg(unix)]
        {
            use std::os::unix::ffi::OsStringExt;
            let non_unicode = OsString::from_vec(vec![b'x', 0x80]);
            assert_eq!(
                ready(ParseArgsPipe.call(vec!["create".into(), non_unicode.clone()])).unwrap(),
                CliAction::Create(vec![non_unicode])
            );
        }
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["enter".into(), "demo".into()])).unwrap(),
            CliAction::Enter(vec!["demo".into()])
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["remove".into(), "demo".into()])).unwrap(),
            CliAction::Remove(vec!["demo".into()])
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["completion".into(), "cr".into()])).unwrap(),
            CliAction::Completion("cr".into())
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["--version".into()])).unwrap(),
            CliAction::Version
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["-h".into()])).unwrap(),
            CliAction::Help
        );
        assert_eq!(
            ready(ParseArgsPipe.call(vec!["help".into()])).unwrap(),
            CliAction::Help
        );
        assert!(ready(ParseArgsPipe.call(vec!["wat".into()])).is_err());
    }

    #[test]
    fn cli_help_list_and_completion_are_consistent() {
        let help = ready(HelpPipe.call(())).unwrap();
        let commands = ready(ListCommandsPipe.call(())).unwrap();
        for command in &commands {
            assert!(help.contains(command));
        }
        assert_eq!(
            ready(CompleteCommandsPipe.call("cr".into())).unwrap(),
            vec!["create"]
        );
        assert_eq!(
            ready(CompleteCommandsPipe.call(OsString::new())).unwrap(),
            commands
        );
    }
}
