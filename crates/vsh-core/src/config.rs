use std::path::PathBuf;

use conflaguration::{Settings, Validate};
use serde::{Deserialize, Serialize};

/// Runtime configuration shared by the vsh CLI and library.
///
/// The CLI will resolve this once and pass the validated value to the library.
/// These owned strings and paths live on the cold configuration path; command
/// execution does not re-resolve environment variables.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize, Settings)]
#[settings(prefix = "VSH")]
#[serde(default)]
pub struct Config {
    #[setting(default)]
    pub venv_name: String,
    #[setting(default)]
    pub venv_path: PathBuf,
    #[setting(default)]
    pub vsh_config_path: PathBuf,
    #[setting(default)]
    pub working_path: Option<PathBuf>,
    #[setting(default)]
    pub interpreter_path: PathBuf,
    #[setting(default)]
    pub shell_path: PathBuf,
    #[setting(default)]
    pub vsh_version: String,
}

// conflaguration's Validate derive cascades into nested/flattened fields. This
// flat config has one value-specific rule, so a manual impl avoids a wrapper
// struct solely to carry a validation attribute the derive does not provide.
impl Validate for Config {
    fn validate(&self) -> conflaguration::Result<()> {
        if self.venv_name.trim().is_empty() {
            return Err(conflaguration::Error::Validation {
                errors: vec![conflaguration::ValidationMessage::new(
                    "venv_name",
                    "must not be empty",
                )],
            });
        }
        Ok(())
    }
}

impl Config {
    /// Resolve the VSH-prefixed environment and explicitly validate it.
    pub fn from_environment() -> conflaguration::Result<Self> {
        conflaguration::builder::<Self>().env().validate().build()
    }

    /// Validate a fluent or library-constructed value before use.
    pub fn from_value(value: Self) -> conflaguration::Result<Self> {
        conflaguration::builder::<Self>()
            .value(value)
            .validate()
            .build()
    }
}

#[cfg(test)]
mod tests {
    use super::Config;

    #[test]
    fn environment_settings_are_resolved_and_validated() {
        temp_env::with_var("VSH_VENV_NAME", Some("demo"), || {
            let config = Config::from_environment()
                .expect("a non-empty VSH_VENV_NAME should produce valid config");
            assert_eq!(config.venv_name, "demo");
        });

        temp_env::with_var("VSH_VENV_NAME", Some("  "), || {
            let result = Config::from_environment();
            assert!(result.is_err(), "blank names must be rejected before use");
        });

        let direct = Config {
            venv_name: String::new(),
            ..Config::default()
        };
        assert!(
            Config::from_value(direct).is_err(),
            "fluent/library-created config must validate too"
        );

        let fluent = Config::from_value(Config {
            venv_name: "fluent".to_owned(),
            ..Config::default()
        })
        .expect("a valid fluent value should pass validation");
        assert_eq!(fluent.venv_name, "fluent");
    }
}
