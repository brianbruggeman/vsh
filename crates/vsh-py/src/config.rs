//! Validated Python projection of `vsh_core::Config`.

use std::future::Future;
use std::path::PathBuf;
use std::task::{Context, Poll, Waker};

use proxima_primitives::pipe::Pipe;
use pyo3::prelude::*;
use vsh_core::{Config, LoadConfigPipe, StoreConfigPipe};

use crate::errors::config_error;

#[pyclass(name = "Config", module = "vsh._vsh", from_py_object)]
#[derive(Clone)]
pub(crate) struct PyConfig {
    inner: Config,
}

#[pymethods]
impl PyConfig {
    #[new]
    #[pyo3(signature = (venv_name, venv_path = PathBuf::new(), vsh_config_path = PathBuf::new(), working_path = None, interpreter_path = PathBuf::new(), shell_path = PathBuf::new(), vsh_version = String::new()))]
    fn new(
        venv_name: String,
        venv_path: PathBuf,
        vsh_config_path: PathBuf,
        working_path: Option<PathBuf>,
        interpreter_path: PathBuf,
        shell_path: PathBuf,
        vsh_version: String,
    ) -> PyResult<Self> {
        let inner = Config {
            venv_name,
            venv_path,
            vsh_config_path,
            working_path,
            interpreter_path,
            shell_path,
            vsh_version,
        };
        let inner = Config::from_value(inner).map_err(config_error)?;
        Ok(Self { inner })
    }

    #[staticmethod]
    fn from_environment() -> PyResult<Self> {
        Config::from_environment()
            .map(|inner| Self { inner })
            .map_err(config_error)
    }

    #[staticmethod]
    fn load(path: PathBuf) -> PyResult<Self> {
        ready(LoadConfigPipe.call(path))
            .map(|inner| Self { inner })
            .map_err(config_error)
    }

    fn store(&self) -> PyResult<()> {
        ready(StoreConfigPipe.call(self.inner.clone())).map_err(config_error)
    }

    #[getter]
    fn venv_name(&self) -> &str {
        &self.inner.venv_name
    }
    #[getter]
    fn venv_path(&self) -> PathBuf {
        self.inner.venv_path.clone()
    }
    #[getter]
    fn vsh_config_path(&self) -> PathBuf {
        self.inner.vsh_config_path.clone()
    }
    #[getter]
    fn working_path(&self) -> Option<PathBuf> {
        self.inner.working_path.clone()
    }
    #[getter]
    fn interpreter_path(&self) -> PathBuf {
        self.inner.interpreter_path.clone()
    }
    #[getter]
    fn shell_path(&self) -> PathBuf {
        self.inner.shell_path.clone()
    }
    #[getter]
    fn vsh_version(&self) -> &str {
        &self.inner.vsh_version
    }

    fn __repr__(&self) -> String {
        format!(
            "Config(venv_name={:?}, venv_path={:?})",
            self.inner.venv_name, self.inner.venv_path
        )
    }
}

fn ready<F: Future>(future: F) -> F::Output {
    let mut context = Context::from_waker(Waker::noop());
    let mut future = core::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => unreachable!("filesystem pipes complete synchronously"),
    }
}
