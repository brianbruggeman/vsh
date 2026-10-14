#[cfg(unix)]
use std::path::Path;
use std::process::{Command, Output};

fn run_vsh(arguments: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_vsh"))
        .args(arguments)
        .output()
        .expect("launch vsh binary")
}

#[cfg(unix)]
fn valid_venv(path: &Path) {
    let (bin, include, site, python) = if cfg!(windows) {
        ("Scripts", "Include", "Lib/site-packages", "python.exe")
    } else {
        ("bin", "include", "lib/python3.12/site-packages", "python")
    };
    std::fs::create_dir_all(path.join(bin)).unwrap();
    std::fs::create_dir_all(path.join(include)).unwrap();
    std::fs::create_dir_all(path.join(site)).unwrap();
    std::fs::write(path.join(bin).join(python), []).unwrap();
    if !cfg!(windows) {
        std::fs::write(path.join(bin).join("activate"), []).unwrap();
    }
}

#[cfg(unix)]
#[test]
fn cli_ephemeral_create_enters_and_cleans_up_after_nonzero_exit() {
    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("ephemeral");
    let output = run_vsh(&[
        "create",
        "--name",
        "ephemeral",
        "--venv-path",
        venv.to_str().unwrap(),
        "--interpreter",
        "python3",
        "--shell",
        "/bin/sh",
        "--ephemeral",
        "--",
        "-c",
        "printf entered; exit 17",
    ]);

    assert_eq!(
        output.status.code(),
        Some(17),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(String::from_utf8(output.stdout).unwrap(), "entered");
    assert!(!venv.exists(), "ephemeral environment must be removed");
}

#[cfg(unix)]
#[test]
fn cli_ephemeral_create_cleans_up_after_successful_exit() {
    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("ephemeral-success");
    let output = run_vsh(&[
        "create",
        "--name",
        "ephemeral-success",
        "--venv-path",
        venv.to_str().unwrap(),
        "--interpreter",
        "python3",
        "--shell",
        "/bin/sh",
        "--ephemeral",
        "--",
        "-c",
        "printf success",
    ]);

    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert_eq!(String::from_utf8(output.stdout).unwrap(), "success");
    assert!(!venv.exists(), "ephemeral environment must be removed");
}

#[cfg(unix)]
#[test]
fn cli_ephemeral_refuses_to_remove_an_existing_environment() {
    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("existing");
    valid_venv(&venv);
    let output = run_vsh(&[
        "create",
        "--name",
        "existing",
        "--venv-path",
        venv.to_str().unwrap(),
        "--interpreter",
        "python3",
        "--ephemeral",
        "--",
        "-c",
        "exit 0",
    ]);

    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("unused path"));
    assert!(venv.join("bin/python").is_file());
}

#[cfg(unix)]
#[test]
fn cli_ephemeral_removes_partial_environment_after_create_failure() {
    use std::os::unix::fs::PermissionsExt;

    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("partial");
    let interpreter = temp.path().join("failing-python");
    std::fs::write(
        &interpreter,
        "#!/bin/sh\nfor target do :; done\nmkdir -p \"$target\"\ntouch \"$target/partial\"\nexit 17\n",
    )
    .unwrap();
    let mut permissions = std::fs::metadata(&interpreter).unwrap().permissions();
    permissions.set_mode(0o755);
    std::fs::set_permissions(&interpreter, permissions).unwrap();

    let output = run_vsh(&[
        "create",
        "--name",
        "partial",
        "--venv-path",
        venv.to_str().unwrap(),
        "--interpreter",
        interpreter.to_str().unwrap(),
        "--ephemeral",
    ]);

    assert_eq!(output.status.code(), Some(2));
    assert!(
        String::from_utf8_lossy(&output.stderr).contains("17"),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(
        !venv.exists(),
        "failed ephemeral create must clean its target"
    );
}

#[cfg(unix)]
#[test]
fn cli_create_keeps_a_valid_environment() {
    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("new-parent").join("persistent");
    let output = run_vsh(&[
        "create",
        "--name",
        "persistent",
        "--venv-path",
        venv.to_str().unwrap(),
        "--interpreter",
        "python3",
    ]);

    assert_eq!(
        output.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    assert!(venv.join("bin/python").is_file());
    assert!(venv.join("pyvenv.cfg").is_file());
}

#[cfg(unix)]
#[test]
fn cli_enter_list_and_remove_use_configured_pipes() {
    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("envs").join("demo");
    valid_venv(&venv);

    let entered = run_vsh(&[
        "enter",
        "--name",
        "demo",
        "--venv-path",
        venv.to_str().unwrap(),
        "--shell",
        "/bin/sh",
        "--",
        "-c",
        "printf '%s|%s' \"$VIRTUAL_ENV\" \"${PATH%%:*}\"; exit 9",
    ]);
    assert_eq!(entered.status.code(), Some(9));
    assert_eq!(
        String::from_utf8(entered.stdout).unwrap(),
        format!("{}|{}", venv.display(), venv.join("bin").display())
    );

    let listed = run_vsh(&[
        "list",
        "--name",
        "demo",
        "--venv-path",
        venv.to_str().unwrap(),
    ]);
    assert_eq!(listed.status.code(), Some(0));
    assert_eq!(
        String::from_utf8(listed.stdout).unwrap().trim(),
        venv.display().to_string()
    );

    let dry_run = run_vsh(&[
        "remove",
        "--name",
        "demo",
        "--venv-path",
        venv.to_str().unwrap(),
        "--dry-run",
    ]);
    assert_eq!(dry_run.status.code(), Some(0));
    assert!(venv.exists(), "dry-run must not advance removal state");

    let removed = run_vsh(&[
        "remove",
        "--name",
        "demo",
        "--venv-path",
        venv.to_str().unwrap(),
    ]);
    assert_eq!(
        removed.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&removed.stderr)
    );
    assert!(!venv.exists());
}

#[cfg(windows)]
#[test]
fn cli_windows_create_discover_enter_and_remove_real_venv_from_config() {
    let temp = tempfile::tempdir().expect("temporary directory");
    let venv = temp.path().join("native venv");
    let config = temp.path().join("vsh-input.toml");
    let sidecar = temp.path().join("native-vsh.cfg");
    std::fs::write(&sidecar, "legacy vsh config").expect("write sidecar");
    let sidecar_path = sidecar.to_string_lossy().replace('\\', "/");
    std::fs::write(
        &config,
        format!(
            "venv_name = 'native demo'\nvenv_path = 'ignored'\ninterpreter_path = 'python'\nshell_path = 'cmd.exe'\nvsh_config_path = '{sidecar_path}'\n"
        ),
    )
    .expect("write TOML config");
    let config = config.to_str().expect("Windows paths are Unicode");
    let venv_path = venv.to_str().expect("Windows paths are Unicode");

    let created = run_vsh(&["create", "--config", config, "--venv-path", venv_path]);
    assert_eq!(
        created.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&created.stderr)
    );
    assert!(venv.join("Scripts/python.exe").is_file());
    assert!(venv.join("Include").is_dir());
    assert!(venv.join("Lib/site-packages").is_dir());
    assert!(venv.join("pyvenv.cfg").is_file());

    let listed = run_vsh(&["list", "--config", config, "--venv-path", venv_path]);
    assert_eq!(
        listed.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&listed.stderr)
    );
    assert_eq!(
        String::from_utf8_lossy(&listed.stdout)
            .trim()
            .to_ascii_lowercase(),
        venv.display().to_string().to_ascii_lowercase()
    );

    let entered = run_vsh(&[
        "enter",
        "--config",
        config,
        "--venv-path",
        venv_path,
        "--",
        "/C",
        "echo \"%VIRTUAL_ENV%\" & echo \"%VSH_VENV_NAME%\" & exit /b 19",
    ]);
    assert_eq!(
        entered.status.code(),
        Some(19),
        "{}",
        String::from_utf8_lossy(&entered.stderr)
    );
    let entered_lines: Vec<_> = String::from_utf8_lossy(&entered.stdout)
        .lines()
        .map(str::trim)
        .map(str::to_ascii_lowercase)
        .collect();
    assert_eq!(entered_lines.len(), 2, "enter output: {entered_lines:?}");
    assert_eq!(
        entered_lines[0].trim_matches('"'),
        venv.display().to_string().to_ascii_lowercase()
    );
    assert_eq!(entered_lines[1], "\"native demo\"");

    let removed = run_vsh(&["remove", "--config", config, "--venv-path", venv_path]);
    assert_eq!(
        removed.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&removed.stderr)
    );
    assert!(!venv.exists(), "remove must delete the created venv");
    assert!(
        !sidecar.exists(),
        "remove must delete configured vsh sidecar"
    );
}
