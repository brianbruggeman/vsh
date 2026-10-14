use std::path::PathBuf;

use conflaguration::{Settings, Validate};
use serde::{Deserialize, Serialize};

/// Inputs that control virtual-environment creation. This is a stable boundary
/// between CLI parsing and the library operation; values are resolved once.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Settings, Validate)]
#[settings(prefix = "VSH_CREATE")]
#[serde(default)]
pub struct CreateOptions {
    pub site_packages: bool,
    pub overwrite: bool,
    pub symlinks: bool,
    pub upgrade: bool,
    pub include_pip: bool,
    pub prompt: Option<String>,
    pub python: Option<PathBuf>,
    pub working: Option<PathBuf>,
}

impl Default for CreateOptions {
    fn default() -> Self {
        Self {
            site_packages: false,
            overwrite: false,
            // The legacy CLI uses symlinks by default on every supported OS.
            symlinks: true,
            upgrade: false,
            include_pip: true,
            prompt: None,
            python: None,
            working: None,
        }
    }
}

impl CreateOptions {
    /// Resolve `VSH_CREATE_*` over the single library default and validate.
    pub fn from_environment() -> conflaguration::Result<Self> {
        conflaguration::builder::<Self>()
            .value(Self::default())
            .env()
            .validate()
            .build()
    }

    /// Validate a fluent or library-created value before use.
    pub fn from_value(value: Self) -> conflaguration::Result<Self> {
        conflaguration::builder::<Self>()
            .value(value)
            .validate()
            .build()
    }
}

/// Inputs that control entering a venv, independent of process effects.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize, Settings, Validate)]
#[settings(prefix = "VSH_ENTER")]
#[serde(default)]
pub struct EnterOptions {
    pub working: Option<PathBuf>,
    pub ignore_working: bool,
}

impl EnterOptions {
    /// Resolve `VSH_ENTER_*` over the single library default and validate.
    pub fn from_environment() -> conflaguration::Result<Self> {
        conflaguration::builder::<Self>()
            .value(Self::default())
            .env()
            .validate()
            .build()
    }

    /// Validate a fluent or library-created value before use.
    pub fn from_value(value: Self) -> conflaguration::Result<Self> {
        conflaguration::builder::<Self>()
            .value(value)
            .validate()
            .build()
    }
}

#[cfg(test)]
mod tests {
    use super::{CreateOptions, EnterOptions};

    #[test]
    fn options_defaults_and_environment_match_serde_and_fluent_values() {
        let defaults = CreateOptions::default();
        assert!(defaults.include_pip);
        assert!(defaults.symlinks);
        assert!(!defaults.site_packages);

        temp_env::with_vars(
            [
                ("VSH_CREATE_INCLUDE_PIP", None::<&str>),
                ("VSH_CREATE_SYMLINKS", None::<&str>),
            ],
            || {
                assert_eq!(CreateOptions::from_environment().unwrap(), defaults);
            },
        );

        temp_env::with_vars(
            [
                ("VSH_CREATE_INCLUDE_PIP", Some("false")),
                ("VSH_CREATE_SYMLINKS", Some("false")),
            ],
            || {
                let env = CreateOptions::from_environment().expect("env overlays defaults");
                assert!(!env.include_pip);
                assert!(!env.symlinks);
                assert!(!env.site_packages);
            },
        );

        let encoded = serde_json::to_string(&defaults).expect("serialize defaults");
        let decoded: CreateOptions = serde_json::from_str(&encoded).expect("restore defaults");
        assert_eq!(decoded, defaults);
        let partial: CreateOptions = serde_json::from_str("{\"include_pip\":false}")
            .expect("missing fields use the shared default");
        assert!(!partial.include_pip);
        assert!(partial.symlinks);

        let created = CreateOptions::from_value(CreateOptions {
            include_pip: false,
            ..CreateOptions::default()
        })
        .expect("fluent create values validate");
        assert!(!created.include_pip);

        let entered = EnterOptions::from_value(EnterOptions {
            ignore_working: true,
            ..EnterOptions::default()
        })
        .expect("fluent/library values validate");
        assert!(entered.ignore_working);

        temp_env::with_var("VSH_ENTER_IGNORE_WORKING", Some("true"), || {
            assert!(
                EnterOptions::from_environment()
                    .expect("enter env overlays defaults")
                    .ignore_working
            );
        });
        let enter_default: EnterOptions =
            serde_json::from_str("{}").expect("empty serialized settings use the shared default");
        assert_eq!(enter_default, EnterOptions::default());
    }
}
