//! Explicitly configured shell child execution.

use std::ffi::OsString;
use std::process::{Command, Output};

use conflaguration::builder;
use proxima_primitives::pipe::Pipe;

use crate::Config;

/// Run a configured shell with caller-resolved arguments and environment.
///
/// The caller owns argument parsing and environment resolution. This pipe
/// validates the supplied config, clears ambient child environment, installs
/// the supplied entries plus vsh's virtual-environment markers, selects the
/// configured working directory, and returns captured output and exit status.
/// Shell arguments are shell syntax, not a safe `argv` boundary. In particular,
/// Windows `cmd.exe /C` consumes the joined tail as command text.
/// The tuple is sufficient input state; no shell-specific wrapper is needed.
#[derive(Debug, Clone, Copy, Default)]
pub struct ShellPipe;

impl Pipe for ShellPipe {
    type In = (Config, Vec<OsString>, Vec<(OsString, OsString)>);
    type Out = Output;
    type Err = conflaguration::Error;

    fn call(
        &self,
        (config, arguments, environment): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let config = builder::<Config>().value(config).validate().build()?;
            if config.shell_path.as_os_str().is_empty() {
                return Err(validation_error(
                    "shell_path",
                    "must be set before running a shell",
                ));
            }
            if config.venv_path.as_os_str().is_empty() {
                return Err(validation_error(
                    "venv_path",
                    "must be set before running a shell",
                ));
            }

            let mut command = Command::new(&config.shell_path);
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;

                let command_is_cmd = config
                    .shell_path
                    .file_name()
                    .is_some_and(|name| name.to_string_lossy().eq_ignore_ascii_case("cmd.exe"));
                let command_is_c = arguments
                    .first()
                    .is_some_and(|argument| argument.to_string_lossy().eq_ignore_ascii_case("/C"));
                if command_is_cmd && command_is_c && arguments.len() > 1 {
                    // `cmd.exe` does not use standard Windows argv escaping.
                    // `/C` treats its remaining tail as shell command text, so
                    // join the caller-supplied shell syntax and pass it raw.
                    command.arg(&arguments[0]);
                    let mut command_line = OsString::from("\"");
                    for (index, argument) in arguments[1..].iter().enumerate() {
                        if index > 0 {
                            command_line.push(" ");
                        }
                        command_line.push(argument);
                    }
                    command_line.push("\"");
                    command.raw_arg(command_line);
                } else {
                    command.args(arguments);
                }
            }
            #[cfg(not(windows))]
            command.args(arguments);
            command.env_clear().envs(environment);
            command.env("VIRTUAL_ENV", &config.venv_path);
            command.env("VSH", &config.venv_name);
            command.env("VSH_VENV_NAME", &config.venv_name);
            command.current_dir(config.working_path.as_ref().unwrap_or(&config.venv_path));
            Ok(command.output()?)
        }
    }
}

fn validation_error(field: &str, message: &str) -> conflaguration::Error {
    conflaguration::Error::Validation {
        errors: vec![conflaguration::ValidationMessage::new(field, message)],
    }
}

#[cfg(test)]
mod tests {
    use core::future::Future;
    use core::task::{Context, Poll, Waker};
    use std::ffi::OsString;
    use std::path::PathBuf;

    use proxima_primitives::pipe::Pipe;

    use super::ShellPipe;
    use crate::Config;

    fn poll_ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("shell pipe completes in one poll"),
        }
    }

    #[cfg(unix)]
    #[test]
    fn shell_pipe_passes_explicit_environment_cwd_and_exit_status() {
        let temp = tempfile::tempdir().expect("temporary directory");
        let venv = temp.path().join(".venv");
        let working = temp.path().join("work");
        std::fs::create_dir_all(&venv).unwrap();
        std::fs::create_dir_all(&working).unwrap();
        let config = Config {
            venv_name: "demo".to_owned(),
            venv_path: venv.clone(),
            shell_path: PathBuf::from("/bin/sh"),
            working_path: Some(working.clone()),
            ..Config::default()
        };
        temp_env::with_var("VSH_AMBIENT_ONLY", Some("must-not-leak"), || {
            let script = "printf '%s|%s|%s|%s|%s' \"$PWD\" \"$VIRTUAL_ENV\" \"$VSH\" \"$VSH_TEST_VALUE\" \"${VSH_AMBIENT_ONLY-unset}\"; exit 23";
            let output = poll_ready(ShellPipe.call((
                config.clone(),
                vec![OsString::from("-c"), OsString::from(script)],
                vec![(OsString::from("VSH_TEST_VALUE"), OsString::from("explicit"))],
            )))
            .expect("the child should launch");

            assert_eq!(output.status.code(), Some(23));
            let stdout = String::from_utf8(output.stdout).unwrap();
            let fields: Vec<_> = stdout.split('|').collect();
            assert_eq!(fields.len(), 5);
            assert_eq!(
                std::fs::canonicalize(fields[0]).unwrap(),
                std::fs::canonicalize(&working).unwrap()
            );
            assert_eq!(
                std::fs::canonicalize(fields[1]).unwrap(),
                std::fs::canonicalize(&venv).unwrap()
            );
            assert_eq!(&fields[2..], ["demo", "explicit", "unset"]);

            let fallback = Config {
                working_path: None,
                ..config
            };
            let output = poll_ready(ShellPipe.call((
                fallback,
                vec![OsString::from("-c"), OsString::from("printf '%s' \"$PWD\"")],
                Vec::new(),
            )))
            .expect("the child should use the venv cwd fallback");
            assert_eq!(output.status.code(), Some(0));
            let cwd = String::from_utf8(output.stdout).unwrap();
            assert_eq!(
                std::fs::canonicalize(cwd).unwrap(),
                std::fs::canonicalize(&venv).unwrap()
            );
        });
    }

    #[cfg(windows)]
    #[test]
    fn shell_pipe_runs_native_windows_child_with_configured_cwd_and_status() {
        let temp = tempfile::tempdir().expect("temporary directory");
        let venv = temp.path().join("venv & with spaces");
        let working = temp.path().join("work & directory");
        std::fs::create_dir_all(&venv).unwrap();
        std::fs::create_dir_all(&working).unwrap();
        let config = Config {
            venv_name: "demo".to_owned(),
            venv_path: venv.clone(),
            shell_path: PathBuf::from("cmd.exe"),
            working_path: Some(working.clone()),
            ..Config::default()
        };
        let command = [
            "echo \"%CD%\" &",
            "echo \"%VIRTUAL_ENV%\" & echo \"%VSH%\" & echo \"%VSH_TEST_VALUE%\" & exit /b 23",
        ];
        let output = poll_ready(ShellPipe.call((
            config,
            vec![
                OsString::from("/C"),
                OsString::from(command[0]),
                OsString::from(command[1]),
            ],
            vec![(
                OsString::from("VSH_TEST_VALUE"),
                OsString::from("explicit & value"),
            )],
        )))
        .expect("cmd.exe should launch");
        assert_eq!(output.status.code(), Some(23));
        assert!(
            output.stderr.is_empty(),
            "unexpected stderr: {:?}",
            output.stderr
        );
        let stdout = String::from_utf8_lossy(&output.stdout);
        let lines: Vec<_> = stdout.lines().map(str::trim).collect();
        assert_eq!(lines.len(), 4, "unexpected cmd.exe output: {stdout:?}");
        assert_eq!(
            lines[0].trim_matches('"').to_ascii_lowercase(),
            working.display().to_string().to_ascii_lowercase()
        );
        assert_eq!(
            lines[1].trim_matches('"').to_ascii_lowercase(),
            venv.display().to_string().to_ascii_lowercase()
        );
        assert_eq!(lines[2], "\"demo\"");
        assert_eq!(lines[3], "\"explicit & value\"");
    }

    #[test]
    fn shell_pipe_rejects_invalid_config_before_launching() {
        let config = Config {
            venv_name: " ".to_owned(),
            venv_path: PathBuf::from("/nonexistent/venv"),
            shell_path: PathBuf::from("/this/must/not/be/launched"),
            ..Config::default()
        };
        let result = poll_ready(ShellPipe.call((config, Vec::new(), Vec::new())));
        assert!(matches!(
            result,
            Err(conflaguration::Error::Validation { .. })
        ));
    }

    #[test]
    fn shell_pipe_rejects_empty_venv_path_before_launching() {
        let config = Config {
            venv_name: "demo".to_owned(),
            shell_path: PathBuf::from("/this/must/not/be/launched"),
            ..Config::default()
        };
        let result = poll_ready(ShellPipe.call((config, Vec::new(), Vec::new())));
        assert!(matches!(
            result,
            Err(conflaguration::Error::Validation { .. })
        ));
    }
}
