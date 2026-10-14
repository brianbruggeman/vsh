use core::task::{Context, Poll, Waker};

use proxima_primitives::pipe::Pipe;
use proxima_telemetry::{emit::EnvFilter, pipes::InMemoryPipe, trace::Status};
use vsh_cli::{CliAction, RunActionPipe};
use vsh_core::Config;

fn ready<F: core::future::Future>(future: F) -> F::Output {
    let mut context = Context::from_waker(Waker::noop());
    let mut future = core::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => panic!("filesystem action unexpectedly yielded"),
    }
}

#[test]
fn telemetry_run_action_records_error_span() {
    let sink = InMemoryPipe::new();
    let recorder = proxima_telemetry::recorder::Recorder::builder()
        .pipe(sink.clone())
        .install()
        .expect("install in-memory process recorder");
    proxima_telemetry::emit::global::install(EnvFilter::parse("trace"));

    let temp = tempfile::tempdir().expect("temporary directory");
    let invalid_venv = temp.path().join("not-a-venv");
    std::fs::create_dir(&invalid_venv).expect("create invalid environment directory");
    let config = Config::from_value(Config {
        venv_name: "telemetry-test".to_owned(),
        venv_path: invalid_venv,
        ..Config::default()
    })
    .expect("valid action configuration");

    let result = ready(RunActionPipe.call((CliAction::Remove(Vec::new()), config)));
    assert!(
        result.is_err(),
        "removing a non-venv should fail in the action"
    );
    recorder.drain();

    let spans = sink.spans();
    assert_eq!(spans.len(), 1, "the actual action should emit one span");
    assert!(matches!(spans[0].status, Status::Error { .. }));
    println!("ACTION_SPAN_COUNT={} STATUS=Error", spans.len());
}
