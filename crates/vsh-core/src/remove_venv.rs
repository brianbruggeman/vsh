//! Remove validated virtual environments through a Proxima filesystem pipe.

use std::fs;
use std::io;

use conflaguration::builder;
use proxima_primitives::pipe::{Pipe, PipeExt};

use crate::{Config, ObserveVenvLayoutPipe, ValidateVenvLayoutPipe};

/// Guard and remove a virtual environment and its configured vsh config file.
///
/// The input is `(Config, dry_run)`. Both inputs are resolved by the caller;
/// this operation explicitly validates `Config`, then composes the C09 layout
/// observer and validator before mutation. The dry-run performs the same safety
/// checks and returns without deleting either path.
#[derive(Debug, Clone, Copy, Default)]
pub struct RemoveVenvPipe;

impl Pipe for RemoveVenvPipe {
    type In = (Config, bool);
    type Out = ();
    type Err = conflaguration::Error;

    fn call(
        &self,
        (config, dry_run): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let config = builder::<Config>().value(config).validate().build()?;
            let valid = proxima_primitives::pipe::Pipe::call(
                &ObserveVenvLayoutPipe.and_then(ValidateVenvLayoutPipe),
                config.venv_path.clone(),
            )
            .await
            .expect("layout observation and validation are infallible");
            if !valid {
                return Err(validation_error(
                    "venv_path",
                    "does not contain a valid virtual environment",
                ));
            }
            if dry_run {
                return Ok(());
            }

            fs::remove_dir_all(&config.venv_path)?;
            match fs::remove_file(&config.vsh_config_path) {
                Ok(()) => Ok(()),
                Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
                Err(error) => Err(error.into()),
            }
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
    use std::fs;
    use std::path::Path;

    use proxima_primitives::pipe::Pipe;

    use super::RemoveVenvPipe;
    use crate::Config;

    fn poll_ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("remove pipe completes in one poll"),
        }
    }

    fn make_valid_layout(path: &Path) {
        let (bin, include, site_packages, python) = if cfg!(windows) {
            ("Scripts", "Include", "Lib/site-packages", "python.exe")
        } else {
            ("bin", "include", "lib/python3.12/site-packages", "python")
        };
        fs::create_dir_all(path.join(bin)).unwrap();
        fs::create_dir_all(path.join(include)).unwrap();
        fs::create_dir_all(path.join(site_packages)).unwrap();
        fs::write(path.join(bin).join(python), []).unwrap();
        if !cfg!(windows) {
            fs::write(path.join(bin).join("activate"), []).unwrap();
        }
    }

    #[test]
    fn remove_venv_guards_invalid_dry_run_and_real_cleanup() {
        let temp = tempfile::tempdir().expect("temporary root");

        let invalid_path = temp.path().join("invalid");
        fs::create_dir(&invalid_path).unwrap();
        let invalid_config_path = temp.path().join("invalid.cfg");
        fs::write(&invalid_config_path, "config").unwrap();
        let invalid = Config {
            venv_name: "invalid".to_owned(),
            venv_path: invalid_path.clone(),
            vsh_config_path: invalid_config_path.clone(),
            ..Config::default()
        };
        assert!(matches!(
            poll_ready(RemoveVenvPipe.call((invalid, false))),
            Err(conflaguration::Error::Validation { .. })
        ));
        assert!(invalid_path.exists());
        assert!(invalid_config_path.exists());

        let missing_config_path = temp.path().join("missing.cfg");
        fs::write(&missing_config_path, "config").unwrap();
        let missing = Config {
            venv_name: "missing".to_owned(),
            venv_path: temp.path().join("missing"),
            vsh_config_path: missing_config_path.clone(),
            ..Config::default()
        };
        assert!(matches!(
            poll_ready(RemoveVenvPipe.call((missing, false))),
            Err(conflaguration::Error::Validation { .. })
        ));
        assert!(missing_config_path.exists());

        let dry_path = temp.path().join("dry");
        make_valid_layout(&dry_path);
        let dry_config_path = temp.path().join("dry.cfg");
        fs::write(&dry_config_path, "config").unwrap();
        let dry = Config {
            venv_name: "dry".to_owned(),
            venv_path: dry_path.clone(),
            vsh_config_path: dry_config_path.clone(),
            ..Config::default()
        };
        let invalid_config = Config {
            venv_name: " ".to_owned(),
            ..dry.clone()
        };
        assert!(matches!(
            poll_ready(RemoveVenvPipe.call((invalid_config, false))),
            Err(conflaguration::Error::Validation { .. })
        ));
        assert!(dry_path.exists());
        assert!(dry_config_path.exists());
        poll_ready(RemoveVenvPipe.call((dry, true))).expect("dry-run passes validation");
        assert!(dry_path.exists());
        assert!(dry_config_path.exists());

        let real_path = temp.path().join("real");
        make_valid_layout(&real_path);
        let real_config_path = temp.path().join("real.cfg");
        fs::write(&real_config_path, "config").unwrap();
        let real = Config {
            venv_name: "real".to_owned(),
            venv_path: real_path.clone(),
            vsh_config_path: real_config_path.clone(),
            ..Config::default()
        };
        poll_ready(RemoveVenvPipe.call((real, false))).expect("valid environment is removed");
        assert!(!real_path.exists());
        assert!(!real_config_path.exists());
    }
}
