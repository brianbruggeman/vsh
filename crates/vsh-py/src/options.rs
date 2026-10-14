//! Validated Python projection of `vsh_core::CreateOptions`.

use std::path::PathBuf;

use pyo3::prelude::*;
use vsh_core::CreateOptions;

use crate::errors::config_error;

#[pyclass(name = "CreateOptions", module = "vsh._vsh", from_py_object)]
#[derive(Clone)]
pub(crate) struct PyCreateOptions {
    inner: CreateOptions,
}

impl PyCreateOptions {
    pub(crate) fn into_inner(self) -> CreateOptions {
        self.inner
    }
}

#[pymethods]
impl PyCreateOptions {
    #[new]
    #[pyo3(signature = (site_packages = false, overwrite = false, symlinks = true, upgrade = false, include_pip = true, prompt = None, python = None, working = None))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        site_packages: bool,
        overwrite: bool,
        symlinks: bool,
        upgrade: bool,
        include_pip: bool,
        prompt: Option<String>,
        python: Option<PathBuf>,
        working: Option<PathBuf>,
    ) -> PyResult<Self> {
        let inner = CreateOptions {
            site_packages,
            overwrite,
            symlinks,
            upgrade,
            include_pip,
            prompt,
            python,
            working,
        };
        let inner = CreateOptions::from_value(inner).map_err(config_error)?;
        Ok(Self { inner })
    }

    #[staticmethod]
    fn from_environment() -> PyResult<Self> {
        CreateOptions::from_environment()
            .map(|inner| Self { inner })
            .map_err(config_error)
    }

    #[getter]
    fn site_packages(&self) -> bool {
        self.inner.site_packages
    }
    #[getter]
    fn overwrite(&self) -> bool {
        self.inner.overwrite
    }
    #[getter]
    fn symlinks(&self) -> bool {
        self.inner.symlinks
    }
    #[getter]
    fn upgrade(&self) -> bool {
        self.inner.upgrade
    }
    #[getter]
    fn include_pip(&self) -> bool {
        self.inner.include_pip
    }
    #[getter]
    fn prompt(&self) -> Option<String> {
        self.inner.prompt.clone()
    }
    #[getter]
    fn python(&self) -> Option<PathBuf> {
        self.inner.python.clone()
    }
    #[getter]
    fn working(&self) -> Option<PathBuf> {
        self.inner.working.clone()
    }
}
