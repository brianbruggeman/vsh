//! Run validated CLI actions by composing the library's Proxima pipes.

use std::ffi::OsString;
use std::io::{self, Write};
use std::path::PathBuf;

use conflaguration::builder;
use proxima_primitives::pipe::Pipe;
use vsh_core::{
    Config, CreateOptions, CreateVenvPipe, DiscoverVenvsPipe, Effect, Event, LifecyclePipe,
    RemoveVenvPipe, ShellPipe, State,
};

use crate::CliAction;

/// Parse create-specific flags while leaving shell arguments after `--`.
#[derive(Debug, Clone, Copy, Default)]
pub struct ParseCreateOptionsPipe;

impl Pipe for ParseCreateOptionsPipe {
    type In = Vec<OsString>;
    type Out = (CreateOptions, bool, Vec<OsString>);
    type Err = conflaguration::Error;

    fn call(
        &self,
        arguments: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let mut options = builder::<CreateOptions>()
                .value(CreateOptions::default())
                .env()
                .build()?;
            let mut ephemeral = false;
            let mut shell_args = Vec::new();
            let mut args = arguments.into_iter();
            while let Some(arg) = args.next() {
                if arg == "--" {
                    shell_args.extend(args);
                    break;
                }
                match arg.to_str() {
                    Some("--ephemeral") => ephemeral = true,
                    Some("--site-packages") => options.site_packages = true,
                    Some("--no-site-packages") => options.site_packages = false,
                    Some("--overwrite") => options.overwrite = true,
                    Some("--upgrade") => options.upgrade = true,
                    Some("--symlinks") => options.symlinks = true,
                    Some("--copies") => options.symlinks = false,
                    Some("--without-pip") => options.include_pip = false,
                    Some("--prompt") => {
                        options.prompt = Some(required_text(&mut args, "--prompt")?);
                    }
                    Some("--python") => {
                        options.python = Some(PathBuf::from(required(&mut args, "--python")?));
                    }
                    Some("--working") => {
                        options.working = Some(PathBuf::from(required(&mut args, "--working")?));
                    }
                    Some(flag) if flag.starts_with('-') => {
                        return Err(validation_error(
                            "args",
                            &format!("unknown create option: {flag}"),
                        ));
                    }
                    _ => shell_args.push(arg),
                }
            }
            options = builder::<CreateOptions>()
                .value(options)
                .validate()
                .build()?;
            Ok((options, ephemeral, shell_args))
        }
    }
}

/// Execute one parsed action using caller-resolved config.
#[derive(Debug, Clone, Copy, Default)]
pub struct RunActionPipe;

impl Pipe for RunActionPipe {
    type In = (CliAction, Config);
    type Out = i32;
    type Err = conflaguration::Error;

    fn call(
        &self,
        (action, config): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            match action {
                CliAction::List(_) => {
                    let root = config.venv_path.parent().ok_or_else(|| {
                        validation_error("venv_path", "must have a parent for list")
                    })?;
                    let paths = Pipe::call(&DiscoverVenvsPipe, root.to_path_buf())
                        .await
                        .expect("discovery pipe is infallible");
                    for path in paths {
                        println!("{}", path.display());
                    }
                    Ok(0)
                }
                CliAction::Create(args) => {
                    let (options, ephemeral, shell_args) =
                        Pipe::call(&ParseCreateOptionsPipe, args).await?;
                    if ephemeral {
                        create_and_enter(config, options, shell_args).await
                    } else {
                        if !shell_args.is_empty() {
                            return Err(validation_error(
                                "args",
                                "shell arguments require --ephemeral",
                            ));
                        }
                        let (state, effect) = transition(State::Absent, Event::Create).await;
                        ensure_effect(effect, Effect::Create)?;
                        Pipe::call(&CreateVenvPipe, (config, options)).await?;
                        let (_, effect) = transition(state, Event::Created).await;
                        ensure_effect(effect, Effect::None)?;
                        Ok(0)
                    }
                }
                CliAction::Enter(args) => enter(config, args).await,
                CliAction::Remove(args) => {
                    let dry_run = args.iter().any(|arg| arg == "--dry-run");
                    if dry_run {
                        Pipe::call(&RemoveVenvPipe, (config, true)).await?;
                        return Ok(0);
                    }
                    let (_, effect) = transition(State::Ready, Event::Remove).await;
                    ensure_effect(effect, Effect::Remove)?;
                    Pipe::call(&RemoveVenvPipe, (config, dry_run)).await?;
                    let (_, effect) = transition(State::Removing, Event::Removed).await;
                    ensure_effect(effect, Effect::None)?;
                    Ok(0)
                }
                _ => Ok(0),
            }
        }
    }
}

async fn enter(config: Config, args: Vec<OsString>) -> Result<i32, conflaguration::Error> {
    let (_, effect) = transition(State::Ready, Event::Enter).await;
    ensure_effect(effect, Effect::Enter)?;
    let args = after_separator(args);
    let environment = child_environment(&config)?;
    let output = Pipe::call(&ShellPipe, (config, args, environment)).await?;
    let (_, effect) = transition(State::Entering, Event::Entered).await;
    ensure_effect(effect, Effect::None)?;
    let (_, effect) = transition(State::Active, Event::Exited).await;
    ensure_effect(effect, Effect::None)?;
    write_output(&output.stdout, &output.stderr);
    Ok(output.status.code().unwrap_or(1))
}

async fn create_and_enter(
    config: Config,
    options: CreateOptions,
    shell_args: Vec<OsString>,
) -> Result<i32, conflaguration::Error> {
    if config.venv_path.exists() {
        return Err(validation_error(
            "venv_path",
            "ephemeral environments require an unused path",
        ));
    }
    let (state, effect) = transition(State::Absent, Event::CreateEphemeral).await;
    ensure_effect(effect, Effect::Create)?;
    let config = match Pipe::call(&CreateVenvPipe, (config.clone(), options)).await {
        Ok(config) => config,
        Err(error) => {
            let (_, effect) = transition(state, Event::Failed).await;
            ensure_effect(effect, Effect::None)?;
            return Err(error);
        }
    };
    let (state, effect) = transition(state, Event::Created).await;
    ensure_effect(effect, Effect::Enter)?;
    let (state, effect) = transition(state, Event::Entered).await;
    ensure_effect(effect, Effect::None)?;
    let output = match async {
        let environment = child_environment(&config)?;
        Pipe::call(
            &ShellPipe,
            (config.clone(), after_separator(shell_args), environment),
        )
        .await
    }
    .await
    {
        Ok(output) => output,
        Err(error) => {
            let (state, effect) = transition(state, Event::Failed).await;
            ensure_effect(effect, Effect::Remove)?;
            Pipe::call(&RemoveVenvPipe, (config, false)).await?;
            let (_, effect) = transition(state, Event::Removed).await;
            ensure_effect(effect, Effect::None)?;
            return Err(error);
        }
    };
    let (state, effect) = transition(state, Event::Exited).await;
    ensure_effect(effect, Effect::Remove)?;
    Pipe::call(&RemoveVenvPipe, (config, false)).await?;
    let (_, effect) = transition(state, Event::Removed).await;
    ensure_effect(effect, Effect::None)?;
    write_output(&output.stdout, &output.stderr);
    Ok(output.status.code().unwrap_or(1))
}

async fn transition(state: State, event: Event) -> (State, Effect) {
    Pipe::call(&LifecyclePipe, (state, event))
        .await
        .expect("lifecycle transitions are infallible")
}

fn ensure_effect(actual: Effect, expected: Effect) -> Result<(), conflaguration::Error> {
    if actual == expected {
        Ok(())
    } else {
        Err(validation_error(
            "lifecycle",
            &format!("expected {expected:?}, got {actual:?}"),
        ))
    }
}

fn required(
    args: &mut impl Iterator<Item = OsString>,
    flag: &str,
) -> Result<OsString, conflaguration::Error> {
    args.next()
        .ok_or_else(|| validation_error("args", &format!("{flag} requires a value")))
}

fn required_text(
    args: &mut impl Iterator<Item = OsString>,
    flag: &str,
) -> Result<String, conflaguration::Error> {
    required(args, flag)?
        .into_string()
        .map_err(|_| validation_error("args", &format!("{flag} must be Unicode")))
}

fn after_separator(args: Vec<OsString>) -> Vec<OsString> {
    match args.iter().position(|arg| arg == "--") {
        Some(index) => args.into_iter().skip(index + 1).collect(),
        None => args,
    }
}

fn child_environment(config: &Config) -> Result<Vec<(OsString, OsString)>, conflaguration::Error> {
    let mut environment: Vec<_> = std::env::vars_os()
        .filter(|(key, _)| !is_path_key(key))
        .collect();
    let path_key = if cfg!(windows) {
        OsString::from("Path")
    } else {
        OsString::from("PATH")
    };
    let mut search_paths =
        vec![
            config
                .venv_path
                .join(if cfg!(windows) { "Scripts" } else { "bin" }),
        ];
    if let Some(path) = std::env::var_os(&path_key) {
        search_paths.extend(std::env::split_paths(&path));
    }
    let path = std::env::join_paths(search_paths)
        .map_err(|error| conflaguration::Error::Io(io::Error::other(error)))?;
    environment.push((path_key, path));
    Ok(environment)
}

fn is_path_key(key: &std::ffi::OsStr) -> bool {
    #[cfg(windows)]
    {
        key.to_string_lossy().eq_ignore_ascii_case("PATH")
    }
    #[cfg(not(windows))]
    {
        key == "PATH"
    }
}

fn write_output(stdout: &[u8], stderr: &[u8]) {
    let _ = io::stdout().write_all(stdout);
    let _ = io::stderr().write_all(stderr);
}

fn validation_error(field: &str, message: &str) -> conflaguration::Error {
    conflaguration::Error::Validation {
        errors: vec![conflaguration::ValidationMessage::new(field, message)],
    }
}
