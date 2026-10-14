//! Create Python virtual environments at an explicit process-effect pipe.

use std::io;
use std::process::Command;

use conflaguration::builder;
use proxima_primitives::pipe::{Pipe, PipeExt};

use crate::{Config, CreateOptions};

/// Run `python -m venv` using already resolved configuration and options.
///
/// The CLI resolves these values and passes them here; this pipe never reads
/// ambient environment configuration. It composes OS process creation with the
/// Proxima layout observer/validator. Use [`Config::from_value`] and
/// [`CreateOptions::from_value`] when constructing values directly.
#[derive(Debug, Clone, Copy, Default)]
pub struct CreateVenvPipe;

impl Pipe for CreateVenvPipe {
    type In = (Config, CreateOptions);
    type Out = Config;
    type Err = conflaguration::Error;

    fn call(
        &self,
        (config, options): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let mut config = builder::<Config>().value(config).validate().build()?;
            let options = builder::<CreateOptions>()
                .value(options)
                .validate()
                .build()?;
            let interpreter = options
                .python
                .as_deref()
                .unwrap_or(config.interpreter_path.as_path());
            if interpreter.as_os_str().is_empty() {
                return Err(validation_error(
                    "interpreter_path",
                    "must be set before creating an environment",
                ));
            }
            if config.venv_path.exists() && !options.overwrite && !options.upgrade {
                return Err(validation_error(
                    "venv_path",
                    "already exists; set overwrite or upgrade to reuse it",
                ));
            }

            let mut command = Command::new(interpreter);
            command.arg("-m").arg("venv");
            if options.site_packages {
                command.arg("--system-site-packages");
            }
            if options.overwrite {
                command.arg("--clear");
            }
            command.arg(if options.symlinks {
                "--symlinks"
            } else {
                "--copies"
            });
            if options.upgrade {
                command.arg("--upgrade");
            }
            if !options.include_pip {
                command.arg("--without-pip");
            }
            command
                .arg("--prompt")
                .arg(options.prompt.as_deref().unwrap_or(&config.venv_name))
                .arg(&config.venv_path);
            let status = command.status()?;
            if !status.success() {
                return Err(conflaguration::Error::Io(io::Error::other(format!(
                    "interpreter exited with status {status}"
                ))));
            }

            let valid = proxima_primitives::pipe::Pipe::call(
                &crate::ObserveVenvLayoutPipe.and_then(crate::ValidateVenvLayoutPipe),
                config.venv_path.clone(),
            )
            .await
            .expect("layout observation and validation are infallible");
            if !valid {
                return Err(validation_error(
                    "venv_path",
                    "interpreter completed but produced an invalid environment layout",
                ));
            }
            config.working_path = options.working.or(config.working_path);
            if let Some(interpreter) = options.python {
                config.interpreter_path = interpreter;
            }
            Ok(config)
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
    use std::path::PathBuf;

    use proxima_primitives::pipe::{Pipe, PipeExt};

    use super::CreateVenvPipe;
    use crate::{Config, CreateOptions, ObserveVenvLayoutPipe, ValidateVenvLayoutPipe};

    fn poll_ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("create pipe completes in one poll"),
        }
    }

    #[test]
    fn create_venv_pipe_runs_python_and_produces_valid_layout() {
        let temp = tempfile::tempdir().expect("temporary root");
        let venv_path = temp.path().join("demo");
        let interpreter = if cfg!(windows) { "python" } else { "python3" };
        let config = Config {
            venv_name: "demo".to_owned(),
            venv_path: venv_path.clone(),
            interpreter_path: PathBuf::from("unused-default"),
            ..Config::default()
        };
        let options = CreateOptions {
            symlinks: !cfg!(windows),
            site_packages: true,
            include_pip: false,
            prompt: Some("demo-prompt".to_owned()),
            python: Some(PathBuf::from(interpreter)),
            working: Some(temp.path().to_path_buf()),
            ..CreateOptions::default()
        };

        let created = poll_ready(CreateVenvPipe.call((config, options)))
            .expect("python -m venv should create a valid environment");
        assert_eq!(created.venv_path, venv_path);
        assert_eq!(created.interpreter_path, PathBuf::from(interpreter));
        assert_eq!(created.working_path, Some(temp.path().to_path_buf()));
        let config_text = std::fs::read_to_string(created.venv_path.join("pyvenv.cfg"))
            .expect("python writes pyvenv.cfg");
        assert!(config_text.contains("include-system-site-packages = true"));
        assert!(config_text.contains("prompt = 'demo-prompt'"));
        let site_packages = if cfg!(windows) {
            created.venv_path.join("Lib/site-packages")
        } else {
            let lib = created.venv_path.join("lib");
            std::fs::read_dir(lib)
                .expect("read lib")
                .next()
                .expect("one versioned lib directory")
                .expect("read lib entry")
                .path()
                .join("site-packages")
        };
        assert!(!site_packages.join("pip").exists());
        if !cfg!(windows) {
            assert!(
                std::fs::symlink_metadata(created.venv_path.join("bin/python"))
                    .expect("python executable exists")
                    .file_type()
                    .is_symlink()
            );
        } else {
            let python_type =
                std::fs::symlink_metadata(created.venv_path.join("Scripts/python.exe"))
                    .expect("python executable exists")
                    .file_type();
            assert!(python_type.is_file());
            assert!(!python_type.is_symlink());
        }
        assert!(
            poll_ready(
                ObserveVenvLayoutPipe
                    .and_then(ValidateVenvLayoutPipe)
                    .call(created.venv_path)
            )
            .expect("layout inspection is infallible")
        );
    }

    #[test]
    fn invalid_config_is_rejected_before_creating_anything() {
        let temp = tempfile::tempdir().expect("temporary root");
        let venv_path = temp.path().join("must-not-exist");
        let config = Config {
            venv_name: " ".to_owned(),
            venv_path: venv_path.clone(),
            interpreter_path: PathBuf::from("python3"),
            ..Config::default()
        };

        let result = poll_ready(CreateVenvPipe.call((config, CreateOptions::default())));
        assert!(matches!(
            result,
            Err(conflaguration::Error::Validation { .. })
        ));
        assert!(
            !venv_path.exists(),
            "invalid config must fail before process effects"
        );
    }
}
