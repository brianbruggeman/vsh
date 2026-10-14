use conflaguration::{ConfigCodegen, Settings};

#[derive(Settings, ConfigCodegen)]
#[settings(prefix = "VSH")]
struct BuildConfig {
    #[setting(default = 32)]
    max_walk_depth: usize,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let config = BuildConfig::from_env()?;
    conflaguration::codegen::rerun_for::<BuildConfig>();
    conflaguration::codegen::write_consts(&config, "limits_generated.rs")?;
    println!(
        "cargo:rustc-env=VSH_MAX_WALK_DEPTH_RESOLVED={}",
        config.max_walk_depth
    );
    Ok(())
}
