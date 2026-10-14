//! The public vsh library surface. The CLI resolves configuration and passes a
//! validated [`Config`] into these APIs; platform effects are added in later cards.

mod config;
mod lifecycle;
mod options;

pub use config::Config;
pub use lifecycle::{Effect, Event, LifecyclePipe, State, transition};
pub use options::{CreateOptions, EnterOptions};
