//! Python exception surface for Rust validation failures.

use pyo3::create_exception;
use pyo3::exceptions::PyException;

create_exception!(_vsh, VshError, PyException, "base exception for vsh errors");
create_exception!(
    _vsh,
    VshConfigError,
    VshError,
    "invalid or unavailable vsh configuration"
);

pub(crate) fn config_error(error: impl std::fmt::Display) -> pyo3::PyErr {
    VshConfigError::new_err(error.to_string())
}
