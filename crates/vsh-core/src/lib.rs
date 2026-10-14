//! The public vsh library surface. The CLI resolves configuration and passes a
//! validated [`Config`] into these APIs; platform effects are added in later cards.

mod config;

pub use config::Config;
