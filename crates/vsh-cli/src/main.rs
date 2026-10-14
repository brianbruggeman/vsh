use core::future::Future;
use core::task::{Context, Poll, Waker};
use std::process::ExitCode;

use proxima_primitives::pipe::Pipe;
use vsh_cli::{CliAction, CompleteCommandsPipe, HelpPipe, ParseArgsPipe};

fn ready<F: Future>(future: F) -> F::Output {
    let mut context = Context::from_waker(Waker::noop());
    let mut future = core::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => unreachable!("CLI pipes are immediately ready"),
    }
}

fn main() -> ExitCode {
    match ready(ParseArgsPipe.call(std::env::args_os().skip(1).collect())) {
        Ok(CliAction::Help) => {
            print!(
                "{}",
                ready(HelpPipe.call(())).expect("infallible help pipe")
            );
            ExitCode::SUCCESS
        }
        Ok(CliAction::Version) => {
            println!("{}", env!("CARGO_PKG_VERSION"));
            ExitCode::SUCCESS
        }
        Ok(CliAction::List) => {
            eprintln!("environment listing requires resolved configuration");
            ExitCode::from(2)
        }
        Ok(CliAction::Completion(prefix)) => {
            for command in
                ready(CompleteCommandsPipe.call(prefix)).expect("infallible completion pipe")
            {
                println!("{command}");
            }
            ExitCode::SUCCESS
        }
        Ok(_) => {
            eprintln!("command effects are not available yet; run `vsh --help`");
            ExitCode::from(2)
        }
        Err(error) => {
            eprintln!("{error}");
            ExitCode::from(2)
        }
    }
}
