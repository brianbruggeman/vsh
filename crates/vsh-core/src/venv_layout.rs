//! Observe and validate Python virtual-environment directory layouts.

use std::fs;
use std::path::{Path, PathBuf};

use proxima_primitives::pipe::Pipe;

/// Facts observed at the filesystem boundary, kept separate from pure validation.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct VenvLayout {
    pub has_bin: bool,
    pub has_include: bool,
    pub has_site_packages: bool,
    pub activation_scripts: usize,
    pub has_python: bool,
}

impl VenvLayout {
    /// Apply vsh's platform-specific structural rule to previously observed facts.
    #[must_use]
    pub fn is_valid(&self) -> bool {
        if !self.has_bin || !self.has_include || !self.has_site_packages {
            return false;
        }
        cfg!(windows) || (self.activation_scripts > 0 && self.has_python)
    }
}

/// Observe a candidate environment using `Scripts`/`Include` on Windows and
/// `bin`/`include` on Unix. Compose with [`ValidateVenvLayoutPipe`] to get the
/// structural verdict; callers needing the individual facts can inspect the
/// output directly.
#[derive(Debug, Clone, Copy, Default)]
pub struct ObserveVenvLayoutPipe;

impl Pipe for ObserveVenvLayoutPipe {
    type In = PathBuf;
    type Out = VenvLayout;
    type Err = std::convert::Infallible;

    fn call(
        &self,
        path: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move { Ok(observe_layout(&path)) }
    }
}

/// Convert observed layout facts to the platform-specific validity verdict.
#[derive(Debug, Clone, Copy, Default)]
pub struct ValidateVenvLayoutPipe;

impl Pipe for ValidateVenvLayoutPipe {
    type In = VenvLayout;
    type Out = bool;
    type Err = std::convert::Infallible;

    fn call(
        &self,
        layout: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move { Ok(layout.is_valid()) }
    }
}

fn observe_layout(path: &Path) -> VenvLayout {
    let bin_name = if cfg!(windows) { "Scripts" } else { "bin" };
    let include_name = if cfg!(windows) { "Include" } else { "include" };
    let bin_dir = path.join(bin_name);
    let has_site_packages = if cfg!(windows) {
        path.join("Lib").join("site-packages").is_dir()
    } else {
        fs::read_dir(path.join("lib")).is_ok_and(|entries| {
            entries
                .flatten()
                .any(|entry| entry.path().join("site-packages").is_dir())
        })
    };
    let activation_scripts = fs::read_dir(&bin_dir).map_or(0, |entries| {
        entries
            .flatten()
            .filter(|entry| {
                entry.file_type().is_ok_and(|kind| kind.is_file())
                    && entry.file_name().to_string_lossy().starts_with("activate")
            })
            .count()
    });
    let python_name = if cfg!(windows) {
        "python.exe"
    } else {
        "python"
    };

    VenvLayout {
        has_bin: bin_dir.is_dir(),
        has_include: path.join(include_name).is_dir(),
        has_site_packages,
        activation_scripts,
        has_python: bin_dir.join(python_name).is_file(),
    }
}

#[cfg(test)]
mod tests {
    use core::future::Future;
    use core::task::{Context, Poll, Waker};
    use std::fs;
    use std::path::Path;

    use proxima_primitives::pipe::{Pipe, PipeExt};

    use super::{ObserveVenvLayoutPipe, ValidateVenvLayoutPipe, VenvLayout};

    fn poll_ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("layout pipes complete in one poll"),
        }
    }

    fn make_layout(root: &Path) {
        let (bin, include, site_packages, python) = if cfg!(windows) {
            ("Scripts", "Include", "Lib/site-packages", "python.exe")
        } else {
            ("bin", "include", "lib/python3.12/site-packages", "python")
        };
        fs::create_dir_all(root.join(bin)).unwrap();
        fs::create_dir_all(root.join(include)).unwrap();
        fs::create_dir_all(root.join(site_packages)).unwrap();
        fs::write(root.join(bin).join(python), []).unwrap();
        if !cfg!(windows) {
            fs::write(root.join(bin).join("activate"), []).unwrap();
        }
    }

    #[test]
    fn venv_layout_pipes_observe_then_validate() {
        let temp = tempfile::tempdir().expect("temporary root");
        make_layout(temp.path());

        let layout = poll_ready(ObserveVenvLayoutPipe.call(temp.path().to_path_buf()))
            .expect("observation is infallible");
        assert!(layout.has_bin);
        assert!(layout.has_include);
        assert!(layout.has_site_packages);
        if !cfg!(windows) {
            assert!(layout.has_python);
            assert_eq!(layout.activation_scripts, 1);
        }
        assert!(
            poll_ready(
                ObserveVenvLayoutPipe
                    .and_then(ValidateVenvLayoutPipe)
                    .call(temp.path().to_path_buf())
            )
            .expect("composed layout check is infallible")
        );

        let complete = VenvLayout {
            has_bin: true,
            has_include: true,
            has_site_packages: true,
            activation_scripts: 1,
            has_python: true,
        };
        assert!(complete.is_valid());
        assert!(
            !VenvLayout {
                has_bin: false,
                ..complete.clone()
            }
            .is_valid()
        );
        assert!(
            !VenvLayout {
                has_include: false,
                ..complete.clone()
            }
            .is_valid()
        );
        assert!(
            !VenvLayout {
                has_site_packages: false,
                ..complete.clone()
            }
            .is_valid()
        );
        if !cfg!(windows) {
            assert!(
                !VenvLayout {
                    activation_scripts: 0,
                    ..complete.clone()
                }
                .is_valid()
            );
            assert!(
                !VenvLayout {
                    has_python: false,
                    ..complete
                }
                .is_valid()
            );

            let activate = temp.path().join("bin/activate");
            fs::remove_file(&activate).unwrap();
            fs::create_dir(&activate).unwrap();
            let observed = poll_ready(ObserveVenvLayoutPipe.call(temp.path().to_path_buf()))
                .expect("observation is infallible");
            assert_eq!(observed.activation_scripts, 0);
            assert!(
                !poll_ready(
                    ObserveVenvLayoutPipe
                        .and_then(ValidateVenvLayoutPipe)
                        .call(temp.path().to_path_buf())
                )
                .expect("composed layout check is infallible")
            );
        }
    }
}
