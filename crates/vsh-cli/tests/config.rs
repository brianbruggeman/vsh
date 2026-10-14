use std::process::Command;

#[test]
fn cli_config_invalid_value_stops_before_deferred_effects() {
    let output = Command::new(env!("CARGO_BIN_EXE_vsh"))
        .args(["create", "--name", " "])
        .output()
        .expect("launch vsh binary");

    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("venv_name"));
    assert!(!stderr.contains("command effects are not available"));
}
