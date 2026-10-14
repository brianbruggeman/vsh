//! Python Venv wrapper delegates environment effects to vsh-core pipes.

use std::ffi::OsString;
use std::future::Future;
use std::path::PathBuf;
use std::task::{Context, Poll, Waker};

use proxima_primitives::pipe::{Pipe, PipeExt};
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use vsh_core::{
    ChildEnvironmentPipe, Config, CreateOptions, CreateVenvPipe, Effect, Event, LifecyclePipe,
    ObserveVenvLayoutPipe, RemoveVenvPipe, ShellPipe, State, ValidateVenvLayoutPipe,
};

use crate::config::PyConfig;
use crate::errors::{config_error, vsh_error};
use crate::options::PyCreateOptions;

#[pyclass(name = "Venv", module = "vsh._vsh", from_py_object)]
#[derive(Clone)]
pub(crate) struct PyVenv {
    config: Config,
}

#[pymethods]
impl PyVenv {
    #[new]
    #[pyo3(signature = (path, name = None, interpreter_path = None, shell_path = None))]
    fn new(
        py: Python<'_>,
        path: PathBuf,
        name: Option<String>,
        interpreter_path: Option<PathBuf>,
        shell_path: Option<PathBuf>,
    ) -> PyResult<Self> {
        let venv_name = name.unwrap_or_else(|| {
            path.file_name()
                .map_or_else(String::new, |part| part.to_string_lossy().into_owned())
        });
        let config = Config {
            vsh_config_path: path.with_file_name(format!(".{venv_name}.vsh.cfg")),
            interpreter_path: interpreter_path.unwrap_or_else(|| {
                py.import("sys")
                    .and_then(|module| module.getattr("executable"))
                    .and_then(|value| value.extract::<PathBuf>())
                    .unwrap_or_else(|_| {
                        PathBuf::from(if cfg!(windows) {
                            "python.exe"
                        } else {
                            "python3"
                        })
                    })
            }),
            shell_path: shell_path.unwrap_or_else(default_shell),
            venv_name,
            venv_path: path,
            ..Config::default()
        };
        let config = Config::from_value(config).map_err(config_error)?;
        Ok(Self { config })
    }

    #[staticmethod]
    fn from_config(config: PyRef<'_, PyConfig>) -> Self {
        Self {
            config: config.inner.clone(),
        }
    }

    #[getter]
    fn name(&self) -> &str {
        &self.config.venv_name
    }

    #[getter]
    fn path(&self) -> PathBuf {
        self.config.venv_path.clone()
    }

    #[pyo3(signature = (options = None))]
    fn create(&mut self, py: Python<'_>, options: Option<PyCreateOptions>) -> PyResult<()> {
        let options = options.map_or_else(CreateOptions::default, PyCreateOptions::into_inner);
        let config = self.config.clone();
        let result = py.detach(|| {
            ready(async {
                require_effect(
                    LifecyclePipe.call((State::Absent, Event::Create)).await,
                    Effect::Create,
                )?;
                let config = match CreateVenvPipe.call((config, options)).await {
                    Ok(config) => config,
                    Err(error) => {
                        require_effect(
                            LifecyclePipe.call((State::Creating, Event::Failed)).await,
                            Effect::None,
                        )?;
                        return Err(error);
                    }
                };
                require_effect(
                    LifecyclePipe.call((State::Creating, Event::Created)).await,
                    Effect::None,
                )?;
                Ok::<_, conflaguration::Error>(config)
            })
        });
        self.config = result.map_err(vsh_error)?;
        Ok(())
    }

    #[pyo3(signature = (command = None))]
    fn enter(
        &self,
        py: Python<'_>,
        command: Option<Vec<String>>,
    ) -> PyResult<(Py<PyBytes>, Py<PyBytes>, i32)> {
        let config = self.config.clone();
        let arguments = command
            .unwrap_or_default()
            .into_iter()
            .map(OsString::from)
            .collect();
        let output = py
            .detach(|| {
                ready(async {
                    let (state, _) = require_effect(
                        LifecyclePipe.call((State::Ready, Event::Enter)).await,
                        Effect::Enter,
                    )?;
                    let environment = match ChildEnvironmentPipe.call(config.clone()).await {
                        Ok(environment) => environment,
                        Err(error) => {
                            require_effect(
                                LifecyclePipe.call((state, Event::Failed)).await,
                                Effect::None,
                            )?;
                            return Err(error);
                        }
                    };
                    let output = match ShellPipe.call((config, arguments, environment)).await {
                        Ok(output) => output,
                        Err(error) => {
                            require_effect(
                                LifecyclePipe.call((state, Event::Failed)).await,
                                Effect::None,
                            )?;
                            return Err(error);
                        }
                    };
                    let (state, _) = require_effect(
                        LifecyclePipe.call((state, Event::Entered)).await,
                        Effect::None,
                    )?;
                    require_effect(
                        LifecyclePipe.call((state, Event::Exited)).await,
                        Effect::None,
                    )?;
                    Ok::<_, conflaguration::Error>(output)
                })
            })
            .map_err(vsh_error)?;
        Ok((
            PyBytes::new(py, &output.stdout).unbind(),
            PyBytes::new(py, &output.stderr).unbind(),
            output.status.code().unwrap_or(1),
        ))
    }

    fn is_valid(&self) -> bool {
        ready(
            ObserveVenvLayoutPipe
                .and_then(ValidateVenvLayoutPipe)
                .call(self.config.venv_path.clone()),
        )
        .expect("layout pipes are infallible")
    }

    #[pyo3(signature = (dry_run = false))]
    fn remove(&self, py: Python<'_>, dry_run: bool) -> PyResult<()> {
        let config = self.config.clone();
        py.detach(|| {
            ready(async {
                if !dry_run {
                    require_effect(
                        LifecyclePipe.call((State::Ready, Event::Remove)).await,
                        Effect::Remove,
                    )?;
                }
                if let Err(error) = RemoveVenvPipe.call((config, dry_run)).await {
                    if !dry_run {
                        require_effect(
                            LifecyclePipe.call((State::Removing, Event::Failed)).await,
                            Effect::None,
                        )?;
                    }
                    return Err(error);
                }
                if !dry_run {
                    require_effect(
                        LifecyclePipe.call((State::Removing, Event::Removed)).await,
                        Effect::None,
                    )?;
                }
                Ok::<_, conflaguration::Error>(())
            })
        })
        .map_err(vsh_error)
    }

    fn __repr__(&self) -> String {
        format!(
            "Venv(name={:?}, path={:?})",
            self.config.venv_name, self.config.venv_path
        )
    }
}

fn require_effect(
    transition: Result<(State, Effect), core::convert::Infallible>,
    expected: Effect,
) -> Result<(State, Effect), conflaguration::Error> {
    let transition = transition.expect("lifecycle pipe is infallible");
    if transition.1 == expected {
        Ok(transition)
    } else {
        Err(conflaguration::Error::Validation {
            errors: vec![conflaguration::ValidationMessage::new(
                "lifecycle",
                "operation is invalid in the current environment state",
            )],
        })
    }
}

fn default_shell() -> PathBuf {
    if cfg!(windows) {
        std::env::var_os("COMSPEC")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("cmd.exe"))
    } else {
        std::env::var_os("SHELL")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("/bin/sh"))
    }
}

fn ready<F: Future>(future: F) -> F::Output {
    let mut context = Context::from_waker(Waker::noop());
    let mut future = core::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => unreachable!("vsh effect pipes complete synchronously"),
    }
}
