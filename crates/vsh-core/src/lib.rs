//! The public vsh library surface. The CLI resolves configuration and passes a
//! validated [`Config`] into these APIs; platform effects are added in later cards.

mod config;
mod config_file;
mod create_venv;
mod lifecycle;
mod limits;
mod options;
mod venv_layout;

pub use config::Config;
pub use config_file::{LoadConfigPipe, StoreConfigPipe};
pub use create_venv::CreateVenvPipe;
pub use lifecycle::{Effect, Event, LifecyclePipe, State, transition};
pub use limits::MAX_WALK_DEPTH;
pub use options::{CreateOptions, EnterOptions};
pub use venv_layout::{ObserveVenvLayoutPipe, ValidateVenvLayoutPipe, VenvLayout};
