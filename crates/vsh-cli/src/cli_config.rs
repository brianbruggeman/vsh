//! Layered CLI configuration using the library's conflaguration settings.

use std::ffi::OsString;
use std::path::PathBuf;

use conflaguration::builder;
use proxima_primitives::pipe::Pipe;
use vsh_core::Config;

/// Extract the config file and recognized config overrides from command args.
#[derive(Debug, Clone, Copy, Default)]
pub struct ParseConfigFlagsPipe;

impl Pipe for ParseConfigFlagsPipe {
    type In = Vec<OsString>;
    type Out = (Option<PathBuf>, Vec<(String, OsString)>, Vec<OsString>);
    type Err = conflaguration::Error;

    fn call(
        &self,
        arguments: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let mut config_file = None;
            let mut overrides = Vec::new();
            let mut remaining = Vec::new();
            let mut arguments = arguments.into_iter();
            while let Some(argument) = arguments.next() {
                if argument == "--" {
                    remaining.push(argument);
                    remaining.extend(arguments);
                    break;
                }
                let Some(flag) = argument.to_str() else {
                    remaining.push(argument);
                    continue;
                };
                let key = match flag {
                    "--config" => "@file",
                    "--name" => "venv_name",
                    "--venv-path" => "venv_path",
                    "--config-path" => "vsh_config_path",
                    "--working-path" => "working_path",
                    "--interpreter" => "interpreter_path",
                    "--shell" => "shell_path",
                    _ => {
                        remaining.push(argument);
                        continue;
                    }
                };
                let value = arguments
                    .next()
                    .ok_or_else(|| config_error(flag, "requires a value"))?;
                if key == "venv_name" && value.to_str().is_none() {
                    return Err(config_error(flag, "must be valid Unicode"));
                }
                if key == "@file" {
                    config_file = Some(PathBuf::from(value));
                } else {
                    overrides.push((key.to_owned(), value));
                }
            }
            Ok((config_file, overrides, remaining))
        }
    }
}

fn config_error(field: &str, message: &str) -> conflaguration::Error {
    conflaguration::Error::Validation {
        errors: vec![conflaguration::ValidationMessage::new(field, message)],
    }
}

/// Resolve file → `VSH_*` environment → CLI overrides, then validate.
#[derive(Debug, Clone, Copy, Default)]
pub struct ResolveConfigPipe;

impl Pipe for ResolveConfigPipe {
    type In = (Option<PathBuf>, Vec<(String, OsString)>, Vec<OsString>);
    type Out = (Config, Vec<OsString>);
    type Err = conflaguration::Error;

    fn call(
        &self,
        (config_file, overrides, remaining): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let mut builder = builder::<Config>().value(Config::default());
            if let Some(path) = config_file {
                builder = builder.file(path);
            }
            builder
                .env()
                .override_with(|config| {
                    for (key, value) in overrides {
                        match key.as_str() {
                            "venv_name" => {
                                config.venv_name = value
                                    .into_string()
                                    .expect("the parser rejects non-Unicode names");
                            }
                            "venv_path" => config.venv_path = PathBuf::from(value),
                            "vsh_config_path" => config.vsh_config_path = PathBuf::from(value),
                            "working_path" => config.working_path = Some(PathBuf::from(value)),
                            "interpreter_path" => config.interpreter_path = PathBuf::from(value),
                            "shell_path" => config.shell_path = PathBuf::from(value),
                            _ => unreachable!("the parser emits only known config keys"),
                        }
                    }
                })
                .validate()
                .build()
                .map(|config| (config, remaining))
        }
    }
}

#[cfg(test)]
mod tests {
    use core::future::Future;
    use core::task::{Context, Poll, Waker};
    use std::ffi::OsString;
    use std::path::PathBuf;

    use proxima_primitives::pipe::Pipe;

    use super::{ParseConfigFlagsPipe, ResolveConfigPipe};

    fn ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("configuration pipes complete in one poll"),
        }
    }

    #[test]
    fn cli_config_precedence_is_file_then_environment_then_flags() {
        let temp = tempfile::tempdir().expect("temporary directory");
        let config_path = temp.path().join("vsh.toml");
        std::fs::write(&config_path, "venv_name = 'from-file'\n").unwrap();
        temp_env::with_var("VSH_VENV_NAME", Some("from-env"), || {
            let args = vec![
                "--config".into(),
                config_path.clone().into_os_string(),
                "--name".into(),
                "from-cli".into(),
            ];
            let input = ready(ParseConfigFlagsPipe.call(args)).expect("flags parse");
            let (config, remaining) = ready(ResolveConfigPipe.call(input)).expect("layers resolve");
            assert!(remaining.is_empty());
            assert_eq!(config.venv_name, "from-cli");
        });

        temp_env::with_var("VSH_VENV_NAME", Some("from-env"), || {
            let file = Some(config_path.clone());
            let (config, _) = ready(ResolveConfigPipe.call((file, Vec::new(), Vec::new())))
                .expect("file and environment resolve");
            assert_eq!(config.venv_name, "from-env");
        });

        temp_env::with_var("VSH_VENV_NAME", None::<&str>, || {
            let (config, _) =
                ready(ResolveConfigPipe.call((Some(config_path), Vec::new(), Vec::new())))
                    .expect("file value resolves without env or flags");
            assert_eq!(config.venv_name, "from-file");
        });
    }

    #[test]
    fn cli_config_rejects_invalid_values_before_effects() {
        temp_env::with_var("VSH_VENV_NAME", None::<&str>, || {
            let parsed = ready(ParseConfigFlagsPipe.call(vec!["--name".into(), " ".into()]))
                .expect("syntactically valid flags");
            assert!(matches!(
                ready(ResolveConfigPipe.call(parsed)),
                Err(conflaguration::Error::Validation { .. })
            ));
        });
    }

    #[test]
    fn cli_config_rejects_missing_file_and_invalid_environment() {
        let missing = PathBuf::from("/this/vsh-config-file-does-not-exist.toml");
        assert!(ready(ResolveConfigPipe.call((Some(missing), Vec::new(), Vec::new()))).is_err());

        temp_env::with_var("VSH_VENV_NAME", Some(" "), || {
            assert!(matches!(
                ready(ResolveConfigPipe.call((None, Vec::new(), Vec::new()))),
                Err(conflaguration::Error::Validation { .. })
            ));
        });
    }

    #[test]
    fn cli_config_rejects_malformed_file() {
        let temp = tempfile::tempdir().expect("temporary directory");
        let malformed = temp.path().join("malformed.toml");
        std::fs::write(&malformed, "venv_name = [").unwrap();
        assert!(ready(ResolveConfigPipe.call((Some(malformed), Vec::new(), Vec::new()))).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn cli_path_flags_preserve_non_unicode_os_strings() {
        use std::os::unix::ffi::OsStringExt;
        temp_env::with_var("VSH_VENV_NAME", Some("demo"), || {
            let path = OsString::from_vec(vec![b'/', b't', b'm', b'p', b'/', 0x80]);
            let parsed = ready(ParseConfigFlagsPipe.call(vec!["--shell".into(), path.clone()]))
                .expect("path flag parses");
            let (config, _) = ready(ResolveConfigPipe.call(parsed)).expect("config validates");
            assert_eq!(config.shell_path, PathBuf::from(path));
        });
    }
}
