use core::future::Future;
use core::task::{Context, Poll, Waker};
use std::ffi::OsString;

use proxima_primitives::pipe::{Pipe, PipeExt};
use proxima_telemetry::error;
use vsh_cli::{
    CliAction, CompleteCommandsPipe, DrainTelemetryPipe, HelpPipe, InstallTelemetryPipe,
    ParseArgsPipe, ParseConfigFlagsPipe, ResolveConfigPipe, ResolveTelemetryConfigPipe,
    RunActionPipe,
};

fn ready<F: Future>(future: F) -> F::Output {
    let mut context = Context::from_waker(Waker::noop());
    let mut future = core::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => unreachable!("CLI pipes are immediately ready"),
    }
}

fn main() {
    let code = match ready(ParseArgsPipe.call(std::env::args_os().skip(1).collect())) {
        Ok(CliAction::Help) => {
            print!(
                "{}",
                ready(HelpPipe.call(())).expect("infallible help pipe")
            );
            0
        }
        Ok(CliAction::Version) => {
            println!("{}", env!("CARGO_PKG_VERSION"));
            0
        }
        Ok(CliAction::List(args)) => run_configured(args, CliAction::List),
        Ok(CliAction::Create(args)) => run_configured(args, CliAction::Create),
        Ok(CliAction::Enter(args)) => run_configured(args, CliAction::Enter),
        Ok(CliAction::Remove(args)) => run_configured(args, CliAction::Remove),
        Ok(CliAction::Completion(prefix)) => {
            for command in
                ready(CompleteCommandsPipe.call(prefix)).expect("infallible completion pipe")
            {
                println!("{command}");
            }
            0
        }
        Err(error) => {
            eprintln!("{error}");
            2
        }
    };
    std::process::exit(code);
}

fn run_configured(args: Vec<OsString>, action: fn(Vec<OsString>) -> CliAction) -> i32 {
    let telemetry = ResolveTelemetryConfigPipe.and_then(InstallTelemetryPipe);
    let recorder = match ready(telemetry.call(())) {
        Ok(recorder) => recorder,
        Err(error) => {
            eprintln!("telemetry initialization failed: {error}");
            return 2;
        }
    };
    let config_pipe = ParseConfigFlagsPipe.and_then(ResolveConfigPipe);
    let code = match ready(config_pipe.call(args)) {
        Ok((config, remaining)) => match ready(RunActionPipe.call((action(remaining), config))) {
            Ok(code) => code,
            Err(error) => {
                error!(%error, "vsh action failed");
                eprintln!("{error}");
                2
            }
        },
        Err(error) => {
            error!(%error, "vsh configuration failed");
            eprintln!("{error}");
            2
        }
    };
    let _drained =
        ready(DrainTelemetryPipe.call(recorder)).expect("telemetry drain pipe is infallible");
    code
}
