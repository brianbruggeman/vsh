//! Python projections of the validated vsh configuration and option types.

mod config;
mod errors;
mod options;
mod venv;

use pyo3::prelude::*;
use std::ffi::OsString;

use crate::config::PyConfig;
use crate::errors::{VshConfigError, VshError};
use crate::options::PyCreateOptions;
use crate::venv::PyVenv;

#[pyfunction]
fn cli(args: Vec<String>) -> i32 {
    vsh_cli::run_args(args.into_iter().map(OsString::from).collect())
}

#[pymodule]
fn _vsh(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    module.add_class::<PyConfig>()?;
    module.add_class::<PyCreateOptions>()?;
    module.add_class::<PyVenv>()?;
    module.add_function(wrap_pyfunction!(cli, module)?)?;
    module.add("VshError", module.py().get_type::<VshError>())?;
    module.add("VshConfigError", module.py().get_type::<VshConfigError>())?;
    Ok(())
}
