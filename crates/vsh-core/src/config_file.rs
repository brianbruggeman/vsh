//! Legacy TOML config persistence at explicit Proxima pipe boundaries.

use std::fs;
use std::path::{Path, PathBuf};

use proxima_primitives::pipe::Pipe;

use crate::Config;

/// Read, parse, repair legacy path fields, then validate the resulting config.
#[derive(Debug, Clone, Copy, Default)]
pub struct LoadConfigPipe;

impl Pipe for LoadConfigPipe {
    type In = PathBuf;
    type Out = Config;
    type Err = conflaguration::Error;

    fn call(
        &self,
        path: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let text = fs::read_to_string(path)?;
            let mut parsed: Config = toml::from_str(&text)?;
            strip_quoted_paths(&mut parsed);
            let config = conflaguration::builder::<Config>()
                .value(parsed)
                .validate()
                .build()?;
            Ok(config)
        }
    }
}

/// Validate and persist a config at its `vsh_config_path`.
#[derive(Debug, Clone, Copy, Default)]
pub struct StoreConfigPipe;

impl Pipe for StoreConfigPipe {
    type In = Config;
    type Out = ();
    type Err = conflaguration::Error;

    fn call(
        &self,
        config: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let config = conflaguration::builder::<Config>()
                .value(config)
                .validate()
                .build()?;
            let path = &config.vsh_config_path;
            if let Some(parent) = path
                .parent()
                .filter(|parent| !parent.as_os_str().is_empty())
            {
                fs::create_dir_all(parent)?;
            }
            let text = toml::to_string(&config).map_err(std::io::Error::other)?;
            fs::write(path, text)?;
            Ok(())
        }
    }
}

fn strip_quoted_paths(config: &mut Config) {
    config.venv_path = strip_quotes(&config.venv_path);
    config.vsh_config_path = strip_quotes(&config.vsh_config_path);
    config.interpreter_path = strip_quotes(&config.interpreter_path);
    config.shell_path = strip_quotes(&config.shell_path);
    config.working_path = config.working_path.as_deref().map(strip_quotes);
}

fn strip_quotes(path: &Path) -> PathBuf {
    let text = path.to_string_lossy();
    match text
        .strip_prefix('"')
        .and_then(|without_prefix| without_prefix.strip_suffix('"'))
    {
        Some(unquoted) => PathBuf::from(unquoted),
        None => path.to_path_buf(),
    }
}

#[cfg(test)]
mod tests {
    use core::future::Future;
    use core::task::{Context, Poll, Waker};
    use std::path::PathBuf;

    use proxima_primitives::pipe::Pipe;

    use super::{LoadConfigPipe, StoreConfigPipe};
    use crate::Config;

    fn poll_ready<F: Future>(future: F) -> F::Output {
        let mut context = Context::from_waker(Waker::noop());
        let mut future = core::pin::pin!(future);
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => value,
            Poll::Pending => panic!("config file pipes complete in one poll"),
        }
    }

    fn fixture(name: &str) -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("tests/fixtures")
            .join(name)
    }

    #[test]
    fn config_file_pipes_load_legacy_store_and_reject_invalid_data() {
        let legacy = poll_ready(LoadConfigPipe.call(fixture("legacy-0.7.1.cfg")))
            .expect("legacy config loads");
        assert_eq!(legacy.venv_name, "demo");
        assert_eq!(
            legacy.venv_path,
            PathBuf::from("/legacy/home/.virtualenvs/demo")
        );
        assert_eq!(legacy.shell_path, PathBuf::from("/bin/sh"));
        assert_eq!(legacy.working_path, Some(PathBuf::from("/legacy/work")));

        let second_legacy =
            poll_ready(LoadConfigPipe.call(fixture("legacy-0.7.2-stale-paths.cfg")))
                .expect("second legacy config loads");
        assert_eq!(second_legacy.venv_name, "test");
        assert_eq!(
            second_legacy.interpreter_path,
            PathBuf::from("/legacy/venvs/vsh/bin/python")
        );

        let temp_dir = tempfile::tempdir().expect("create isolated temp directory");
        let destination = temp_dir.path().join("stored.cfg");
        let to_store = Config {
            venv_name: "stored".to_owned(),
            venv_path: PathBuf::from("/venvs/stored\""),
            vsh_config_path: destination.clone(),
            interpreter_path: PathBuf::from("/python"),
            shell_path: PathBuf::from("/bin/sh"),
            vsh_version: "0.8.0".to_owned(),
            ..Config::default()
        };
        poll_ready(StoreConfigPipe.call(to_store.clone())).expect("config stores");
        let stored =
            poll_ready(LoadConfigPipe.call(destination.clone())).expect("stored config reloads");
        assert_eq!(stored, to_store);
        let serialized = std::fs::read_to_string(&destination).expect("read stored text");
        assert!(serialized.contains("venv_path = '/venvs/stored\"'"));
        assert!(!serialized.contains("\\\"/venvs/stored"));

        let mut repaired_legacy = legacy.clone();
        repaired_legacy.vsh_config_path = temp_dir.path().join("legacy-roundtrip.cfg");
        poll_ready(StoreConfigPipe.call(repaired_legacy.clone()))
            .expect("repaired legacy config stores");
        let canonical_text =
            std::fs::read_to_string(&repaired_legacy.vsh_config_path).expect("read canonical TOML");
        assert!(canonical_text.contains("venv_path = \"/legacy/home/.virtualenvs/demo\""));
        assert!(!canonical_text.contains("\\\"/legacy/home/.virtualenvs/demo\\\""));
        assert_eq!(
            poll_ready(LoadConfigPipe.call(repaired_legacy.vsh_config_path.clone()))
                .expect("canonical legacy roundtrip loads"),
            repaired_legacy
        );

        assert!(poll_ready(LoadConfigPipe.call(fixture("invalid.cfg"))).is_err());
        let invalid_store_path = temp_dir.path().join("invalid-store.cfg");
        let invalid = Config {
            venv_name: "  ".to_owned(),
            vsh_config_path: invalid_store_path.clone(),
            ..Config::default()
        };
        assert!(poll_ready(StoreConfigPipe.call(invalid)).is_err());
        assert!(
            !invalid_store_path.exists(),
            "invalid config must not be written"
        );
    }
}
