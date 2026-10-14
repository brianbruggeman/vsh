//! Resolve an explicit child environment with the configured venv at the front of PATH.

use std::ffi::{OsStr, OsString};
use std::io;

use conflaguration::builder;
use proxima_primitives::pipe::Pipe;

use crate::Config;

/// Build child environment entries for a caller-supplied `ShellPipe` invocation.
///
/// Centralizing this transform lets the CLI and library bindings activate the same
/// environment without mutating the parent process or duplicating PATH logic.
#[derive(Debug, Clone, Copy, Default)]
pub struct ChildEnvironmentPipe;

impl Pipe for ChildEnvironmentPipe {
    type In = Config;
    type Out = Vec<(OsString, OsString)>;
    type Err = conflaguration::Error;

    fn call(
        &self,
        config: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let config = builder::<Config>().value(config).validate().build()?;
            let path_key = if cfg!(windows) {
                OsString::from("Path")
            } else {
                OsString::from("PATH")
            };
            let mut environment: Vec<_> = std::env::vars_os()
                .filter(|(key, _)| !is_path_key(key))
                .collect();
            let mut search_paths =
                vec![
                    config
                        .venv_path
                        .join(if cfg!(windows) { "Scripts" } else { "bin" }),
                ];
            if let Some(path) = std::env::var_os(&path_key) {
                search_paths.extend(std::env::split_paths(&path));
            }
            let path = std::env::join_paths(search_paths)
                .map_err(|error| conflaguration::Error::Io(io::Error::other(error)))?;
            environment.push((path_key, path));
            Ok(environment)
        }
    }
}

fn is_path_key(key: &OsStr) -> bool {
    #[cfg(windows)]
    {
        key.to_string_lossy().eq_ignore_ascii_case("PATH")
    }
    #[cfg(not(windows))]
    {
        key == "PATH"
    }
}

#[cfg(test)]
mod tests {
    use core::future::Future;
    use core::task::{Context, Poll, Waker};
    use std::path::PathBuf;

    use proxima_primitives::pipe::Pipe;

    use super::ChildEnvironmentPipe;
    use crate::Config;

    fn ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("environment pipe completes immediately"),
        }
    }

    #[test]
    fn child_environment_pipe_prepends_the_configured_venv_path() {
        let config = Config {
            venv_name: "demo".to_owned(),
            venv_path: PathBuf::from("/tmp/demo"),
            ..Config::default()
        };
        let environment = ready(ChildEnvironmentPipe.call(config)).unwrap();
        let path = environment
            .iter()
            .find(|(key, _)| {
                #[cfg(windows)]
                {
                    key.to_string_lossy().eq_ignore_ascii_case("PATH")
                }
                #[cfg(not(windows))]
                {
                    key == "PATH"
                }
            })
            .map(|(_, value)| value)
            .expect("PATH entry");
        let bin = if cfg!(windows) { "Scripts" } else { "bin" };
        assert_eq!(
            std::env::split_paths(path).next(),
            Some(PathBuf::from("/tmp/demo").join(bin))
        );
    }
}
