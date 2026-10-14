use vsh_cli::run_args;

fn main() {
    let code = run_args(std::env::args_os().skip(1).collect());
    std::process::exit(code);
}
