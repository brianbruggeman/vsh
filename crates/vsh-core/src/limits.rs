//! Build-time settings for bounded discovery.

/// Constants emitted by the conflaguration `ConfigCodegen` derive in `build.rs`.
pub mod sized {
    include!(concat!(env!("OUT_DIR"), "/limits_generated.rs"));
}

/// Maximum directory nesting the discovery walker descends.
pub const MAX_WALK_DEPTH: usize = sized::MAX_WALK_DEPTH;

#[cfg(test)]
mod tests {
    use super::{MAX_WALK_DEPTH, sized};

    #[test]
    fn exported_walk_depth_matches_conflaguration_build_resolution() {
        let resolved = env!("VSH_MAX_WALK_DEPTH_RESOLVED")
            .parse::<usize>()
            .expect("build.rs emits the resolved integer setting");
        assert_eq!(sized::MAX_WALK_DEPTH, resolved);
        assert_eq!(MAX_WALK_DEPTH, resolved);
    }
}
