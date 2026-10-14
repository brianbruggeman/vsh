//! Proxima recorder and filter setup for CLI execution.

use std::sync::Arc;

use conflaguration::Validate;
use proxima_primitives::pipe::Pipe;
use proxima_telemetry::emit::{CompiledEmit, EmitConfig};
use proxima_telemetry::recorder::Recorder;

/// Resolve the Proxima `EMIT_*` settings before any CLI action starts.
#[derive(Debug, Clone, Copy, Default)]
pub struct ResolveTelemetryConfigPipe;

impl Pipe for ResolveTelemetryConfigPipe {
    type In = ();
    type Out = EmitConfig;
    type Err = String;

    fn call(
        &self,
        (): Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            let config = EmitConfig::layered()
                .from_env()
                .map_err(|error| error.to_string())?
                .build();
            config.validate().map_err(|error| error.to_string())?;
            config.compile().map_err(|error| error.to_string())?;
            Ok(config)
        }
    }
}

/// Install the configured Proxima process recorder and runtime filter.
#[derive(Debug, Clone, Copy, Default)]
pub struct InstallTelemetryPipe;

impl Pipe for InstallTelemetryPipe {
    type In = EmitConfig;
    type Out = Arc<Recorder>;
    type Err = String;

    fn call(
        &self,
        config: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            config.validate().map_err(|error| error.to_string())?;
            let filter: CompiledEmit = config.compile().map_err(|error| error.to_string())?;
            let recorder = proxima_telemetry::export::install_console_recorder()
                .map_err(|error| error.to_string())?;
            proxima_telemetry::emit::global::install(filter);
            Ok(recorder)
        }
    }
}

/// Drain buffered records before the CLI process exits.
#[derive(Debug, Clone, Copy, Default)]
pub struct DrainTelemetryPipe;

impl Pipe for DrainTelemetryPipe {
    type In = Arc<Recorder>;
    type Out = usize;
    type Err = core::convert::Infallible;

    fn call(
        &self,
        recorder: Self::In,
    ) -> impl core::future::Future<Output = Result<Self::Out, Self::Err>> {
        async move {
            // Proxima's drain is one batch pass; continue until no ring has
            // records left so a busy action cannot strand its final error.
            let mut drained = 0;
            loop {
                let pass = recorder.drain();
                drained += pass;
                if pass == 0 {
                    return Ok(drained);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use proxima_primitives::pipe::Pipe;
    use proxima_telemetry::{capture::capture, emit::EnvFilter, error, instrument, trace::Status};

    use super::ResolveTelemetryConfigPipe;
    use crate::ready;

    #[instrument(recorder = recorder, err, level = "info")]
    fn observed_failure(
        recorder: &proxima_telemetry::recorder::Recorder,
    ) -> Result<(), &'static str> {
        error!(
            recorder = recorder,
            "captured vsh failure",
            operation = "create"
        );
        Err("expected test failure")
    }

    #[test]
    fn configured_recorder_captures_span_and_error_log() {
        proxima_telemetry::emit::global::install(EnvFilter::parse("trace"));
        let captured = capture(|recorder| {
            assert_eq!(observed_failure(recorder), Err("expected test failure"));
        });
        let spans = captured.spans();
        assert_eq!(spans.len(), 1);
        assert!(matches!(spans[0].status, Status::Error { .. }));
        assert_eq!(captured.logs().len(), 1);
        assert!(captured.dump().contains("captured vsh failure"));
    }

    #[test]
    fn ambient_emit_without_default_recorder_is_noop() {
        assert!(proxima_telemetry::export::default_recorder().is_none());
        error!("there is no installed process recorder");
        assert!(proxima_telemetry::export::default_recorder().is_none());
    }

    #[test]
    fn telemetry_filter_settings_resolve_and_validate_from_environment() {
        temp_env::with_var("EMIT_DEFAULT", Some("debug"), || {
            let config = ready(ResolveTelemetryConfigPipe.call(())).unwrap();
            assert_eq!(config.default, "debug");
            assert!(config.compile().is_ok());
        });
    }

    #[test]
    fn telemetry_filter_rejects_invalid_level_before_recorder_install() {
        temp_env::with_var("EMIT_DEFAULT", Some("not-a-level"), || {
            assert!(ready(ResolveTelemetryConfigPipe.call(())).is_err());
        });
    }
}
