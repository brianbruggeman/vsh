//! Bounded, caller-configured filesystem discovery pipes.

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};

use conflaguration::builder;
use proxima_primitives::pipe::{Pipe, PipeExt};

use crate::{Config, MAX_WALK_DEPTH, ObserveVenvLayoutPipe, ValidateVenvLayoutPipe};

/// Find valid venv directories below a root, pruning each discovered venv.
///
/// The traversal follows directory symlinks but tracks canonical directories
/// and stops at [`MAX_WALK_DEPTH`]. It uses the C09 layout pipes for each
/// candidate. Reach for this pipe when a caller needs the sorted inventory;
/// pass a preconfigured root instead of relying on ambient `WORKON_HOME`.
#[derive(Debug, Clone, Copy, Default)]
pub struct DiscoverVenvsPipe;

impl Pipe for DiscoverVenvsPipe {
    type In = PathBuf;
    type Out = Vec<PathBuf>;
    type Err = std::convert::Infallible;

    fn call(
        &self,
        root: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let mut pending = vec![(root, 0usize)];
            let mut visited = HashSet::new();
            let mut found = Vec::new();
            while let Some((directory, depth)) = pending.pop() {
                if depth >= MAX_WALK_DEPTH {
                    continue;
                }
                let key = fs::canonicalize(&directory).unwrap_or_else(|_| directory.clone());
                if !visited.insert(key) {
                    continue;
                }
                let Ok(entries) = fs::read_dir(&directory) else {
                    continue;
                };
                for entry in entries.flatten() {
                    let path = entry.path();
                    if !path.is_dir() {
                        continue;
                    }
                    let valid = Pipe::call(
                        &ObserveVenvLayoutPipe.and_then(ValidateVenvLayoutPipe),
                        path.clone(),
                    )
                    .await
                    .expect("layout observation and validation are infallible");
                    if valid {
                        found.push(path);
                    } else if depth < MAX_WALK_DEPTH {
                        pending.push((path, depth + 1));
                    }
                }
            }
            found.sort();
            Ok(found)
        }
    }
}

/// Resolve stale configured interpreter and shell paths from caller-supplied
/// search directories, preserving either configured executable when it exists.
#[derive(Debug, Clone, Copy, Default)]
pub struct ResolveExecutablesPipe;

impl Pipe for ResolveExecutablesPipe {
    type In = (Config, Vec<PathBuf>);
    type Out = Config;
    type Err = conflaguration::Error;

    fn call(
        &self,
        (config, search_directories): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let mut config = builder::<Config>().value(config).validate().build()?;
            if !is_executable(&config.interpreter_path) {
                config.interpreter_path = find_executable(
                    &search_directories,
                    &config.interpreter_path,
                    interpreter_names(),
                )
                .ok_or_else(|| {
                    validation_error("interpreter_path", "no Python executable found")
                })?;
            }
            if !is_executable(&config.shell_path) {
                config.shell_path =
                    find_executable(&search_directories, &config.shell_path, shell_names())
                        .ok_or_else(|| {
                            validation_error("shell_path", "no shell executable found")
                        })?;
            }
            Ok(config)
        }
    }
}

/// Find `.vshrc` files from ordered caller-supplied roots, followed by the
/// configured venv path. A `.vshrc` may be one file or a directory of files.
#[derive(Debug, Clone, Copy, Default)]
pub struct FindVshrcFilesPipe;

impl Pipe for FindVshrcFilesPipe {
    type In = (Config, Vec<PathBuf>);
    type Out = Vec<PathBuf>;
    type Err = conflaguration::Error;

    fn call(
        &self,
        (config, mut roots): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let config = builder::<Config>().value(config).validate().build()?;
            if !config.venv_path.as_os_str().is_empty() {
                roots.push(config.venv_path);
            }
            let mut seen = HashSet::new();
            let mut files = Vec::new();
            for root in roots {
                let candidate = root.join(".vshrc");
                if candidate.is_file() {
                    push_unique(&candidate, &mut seen, &mut files);
                } else if let Ok(entries) = fs::read_dir(&candidate) {
                    let mut nested: Vec<PathBuf> = entries
                        .flatten()
                        .map(|entry| entry.path())
                        .filter(|path| path.is_file())
                        .collect();
                    nested.sort();
                    for path in nested {
                        push_unique(&path, &mut seen, &mut files);
                    }
                }
            }
            Ok(files)
        }
    }
}

fn push_unique(path: &Path, seen: &mut HashSet<PathBuf>, files: &mut Vec<PathBuf>) {
    let key = fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf());
    if seen.insert(key) {
        files.push(path.to_path_buf());
    }
}

fn find_executable(directories: &[PathBuf], preferred: &Path, names: &[&str]) -> Option<PathBuf> {
    if let Some(name) = preferred.file_name() {
        if let Some(path) = directories
            .iter()
            .map(|directory| directory.join(name))
            .find(|path| is_executable(path))
        {
            return Some(path);
        }
    }
    directories
        .iter()
        .flat_map(|directory| names.iter().map(move |name| directory.join(name)))
        .find(|path| is_executable(path))
}

fn is_executable(path: &Path) -> bool {
    if !path.is_file() {
        return false;
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::metadata(path).is_ok_and(|metadata| metadata.permissions().mode() & 0o111 != 0)
    }
    #[cfg(not(unix))]
    {
        true
    }
}

#[cfg(windows)]
fn interpreter_names() -> &'static [&'static str] {
    &["python.exe", "python3.exe"]
}
#[cfg(not(windows))]
fn interpreter_names() -> &'static [&'static str] {
    &["python3", "python"]
}

#[cfg(windows)]
fn shell_names() -> &'static [&'static str] {
    &["pwsh.exe", "powershell.exe", "cmd.exe"]
}
#[cfg(not(windows))]
fn shell_names() -> &'static [&'static str] {
    &["bash", "sh"]
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
    #[cfg(unix)]
    use std::os::unix::fs::{PermissionsExt, symlink};
    use std::path::{Path, PathBuf};

    use proxima_primitives::pipe::Pipe;

    use super::{DiscoverVenvsPipe, FindVshrcFilesPipe, ResolveExecutablesPipe};
    use crate::Config;

    fn poll_ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("discovery pipes complete in one poll"),
        }
    }

    fn executable(path: &Path) {
        fs::write(path, "fixture").unwrap();
        #[cfg(unix)]
        fs::set_permissions(path, fs::Permissions::from_mode(0o755)).unwrap();
    }

    fn valid_venv(path: &Path) {
        let (bin, include, site, python) = if cfg!(windows) {
            ("Scripts", "Include", "Lib/site-packages", "python.exe")
        } else {
            ("bin", "include", "lib/python3.12/site-packages", "python")
        };
        fs::create_dir_all(path.join(bin)).unwrap();
        fs::create_dir_all(path.join(include)).unwrap();
        fs::create_dir_all(path.join(site)).unwrap();
        fs::write(path.join(bin).join(python), []).unwrap();
        if !cfg!(windows) {
            fs::write(path.join(bin).join("activate"), []).unwrap();
        }
    }

    fn path_at_depth(root: &Path, depth: usize, leaf: &str) -> PathBuf {
        let mut path = root.to_path_buf();
        for index in 1..depth {
            path.push(format!("d{index}"));
        }
        path.push(leaf);
        path
    }

    #[test]
    fn discovery_pipes_bound_walk_resolve_stale_paths_and_order_vshrc() {
        let temp = tempfile::tempdir().expect("temporary root");
        let root = temp.path().join("envs");
        let same_a = root.join("a/same");
        let same_b = root.join("b/same");
        let alpha = root.join("alpha");
        let venv = root.join("zeta");
        valid_venv(&same_b);
        valid_venv(&same_a);
        valid_venv(&alpha);
        valid_venv(&venv);
        let nested_venv = if cfg!(windows) {
            venv.join("Lib/site-packages/nested")
        } else {
            venv.join("lib/python3.12/site-packages/nested")
        };
        valid_venv(&nested_venv);
        let near_limit = path_at_depth(&root, crate::MAX_WALK_DEPTH, "near-limit");
        let beyond_limit = path_at_depth(&root, crate::MAX_WALK_DEPTH + 1, "beyond-limit");
        valid_venv(&near_limit);
        valid_venv(&beyond_limit);
        #[cfg(unix)]
        {
            fs::create_dir_all(root.join("branch")).unwrap();
            symlink(&root, root.join("branch/loop")).unwrap();
        }
        let found = poll_ready(DiscoverVenvsPipe.call(root.clone())).unwrap();
        assert_eq!(found, [same_a, alpha, same_b, near_limit, venv.clone()]);
        assert!(!found.contains(&beyond_limit));

        let bin = temp.path().join("bin");
        fs::create_dir(&bin).unwrap();
        let python = bin.join(if cfg!(windows) {
            "python3.99.exe"
        } else {
            "python3.99"
        });
        let shell = bin.join(if cfg!(windows) { "zsh.exe" } else { "zsh" });
        let fallback_python = bin.join(if cfg!(windows) {
            "python.exe"
        } else {
            "python3"
        });
        let fallback_shell = bin.join(if cfg!(windows) { "cmd.exe" } else { "bash" });
        executable(&python);
        executable(&shell);
        executable(&fallback_python);
        executable(&fallback_shell);
        let stale = Config {
            venv_name: "demo".to_owned(),
            interpreter_path: temp.path().join(if cfg!(windows) {
                "deleted/python3.99.exe"
            } else {
                "deleted/python3.99"
            }),
            shell_path: temp.path().join(if cfg!(windows) {
                "deleted/zsh.exe"
            } else {
                "deleted/zsh"
            }),
            ..Config::default()
        };
        let resolved = poll_ready(ResolveExecutablesPipe.call((stale, vec![bin.clone()])))
            .expect("stale paths fall back to caller search directories");
        assert_eq!(resolved.interpreter_path, python);
        assert_eq!(resolved.shell_path, shell);
        let preserved = poll_ready(ResolveExecutablesPipe.call((resolved.clone(), Vec::new())))
            .expect("configured executable files are preserved without search roots");
        assert_eq!(preserved, resolved);
        let generic_fallback = Config {
            interpreter_path: temp.path().join("deleted/python4"),
            shell_path: temp.path().join("deleted/fish"),
            ..resolved
        };
        let generic =
            poll_ready(ResolveExecutablesPipe.call((generic_fallback, vec![bin.clone()])))
                .expect("missing versions fall back to platform defaults");
        assert_eq!(generic.interpreter_path, fallback_python);
        assert_eq!(generic.shell_path, fallback_shell);

        let first_root = temp.path().join("first");
        let second_root = temp.path().join("second");
        fs::create_dir_all(&first_root).unwrap();
        fs::create_dir_all(&second_root.join(".vshrc")).unwrap();
        fs::write(first_root.join(".vshrc"), "first").unwrap();
        fs::write(second_root.join(".vshrc/z.sh"), "z").unwrap();
        fs::write(second_root.join(".vshrc/a.sh"), "a").unwrap();
        fs::create_dir_all(venv.join(".vshrc")).unwrap();
        fs::write(venv.join(".vshrc/local.sh"), "local").unwrap();
        let config = Config {
            venv_name: "zeta".to_owned(),
            venv_path: venv,
            ..Config::default()
        };
        let files = poll_ready(FindVshrcFilesPipe.call((
            config,
            vec![first_root.clone(), second_root.clone(), first_root],
        )))
        .unwrap();
        let names: Vec<_> = files
            .iter()
            .map(|path| path.file_name().unwrap().to_string_lossy().into_owned())
            .collect();
        assert_eq!(names, [".vshrc", "a.sh", "z.sh", "local.sh"]);
    }
}
