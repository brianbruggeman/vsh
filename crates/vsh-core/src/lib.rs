//! The public vsh library surface. The CLI resolves configuration and passes a
//! validated [`Config`] into these APIs; platform effects are added in later cards.

mod child_environment;
mod config;
mod config_file;
mod create_venv;
mod discovery;
mod lifecycle;
mod limits;
mod options;
mod remove_venv;
mod shell;
mod venv_layout;

pub use child_environment::ChildEnvironmentPipe;
pub use config::Config;
pub use config_file::{LoadConfigPipe, StoreConfigPipe};
pub use create_venv::CreateVenvPipe;
pub use discovery::{DiscoverVenvsPipe, FindVshrcFilesPipe, ResolveExecutablesPipe};
pub use lifecycle::{Effect, Event, LifecyclePipe, State, transition};
pub use limits::MAX_WALK_DEPTH;
pub use options::{CreateOptions, EnterOptions};
pub use remove_venv::RemoveVenvPipe;
pub use shell::ShellPipe;
pub use venv_layout::{ObserveVenvLayoutPipe, ValidateVenvLayoutPipe, VenvLayout};
