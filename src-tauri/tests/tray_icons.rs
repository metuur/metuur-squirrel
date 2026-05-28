//! Asset verification for Story 2.1.
//!
//! All four tray-icon states must exist at both 16x16 (menu bar 1x) and 32x32
//! (Retina @2x), and must decode cleanly via the `image` crate. This catches
//! accidentally-deleted assets, broken regeneration runs, and dimension drift.

use std::path::PathBuf;

const STATES: &[&str] = &["normal", "notification", "processing", "error"];

fn tray_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("icons/tray")
}

#[test]
fn all_state_variants_exist_and_decode_at_1x() {
    let dir = tray_dir();
    for state in STATES {
        let path = dir.join(format!("{state}.png"));
        let img = image::open(&path)
            .unwrap_or_else(|e| panic!("could not open {}: {e}", path.display()));
        assert_eq!(
            img.width(),
            16,
            "{state}.png must be 16px wide, got {}",
            img.width()
        );
        assert_eq!(
            img.height(),
            16,
            "{state}.png must be 16px tall, got {}",
            img.height()
        );
    }
}

#[test]
fn all_state_variants_exist_and_decode_at_2x() {
    let dir = tray_dir();
    for state in STATES {
        let path = dir.join(format!("{state}@2x.png"));
        let img = image::open(&path)
            .unwrap_or_else(|e| panic!("could not open {}: {e}", path.display()));
        assert_eq!(
            img.width(),
            32,
            "{state}@2x.png must be 32px wide, got {}",
            img.width()
        );
        assert_eq!(
            img.height(),
            32,
            "{state}@2x.png must be 32px tall, got {}",
            img.height()
        );
    }
}

#[test]
fn state_variants_are_pairwise_distinct() {
    // If the regeneration pipeline ever produced identical PNGs for two states,
    // R-2.1 ("THE SYSTEM SHALL support exactly four SQ icon states") is silently
    // violated. Cheapest check: every pair of @2x PNGs must differ as raw bytes.
    let dir = tray_dir();
    let bytes: Vec<(String, Vec<u8>)> = STATES
        .iter()
        .map(|s| {
            let p = dir.join(format!("{s}@2x.png"));
            (s.to_string(), std::fs::read(&p).expect("read variant"))
        })
        .collect();

    for i in 0..bytes.len() {
        for j in (i + 1)..bytes.len() {
            assert_ne!(
                bytes[i].1, bytes[j].1,
                "{} and {} must not be byte-identical",
                bytes[i].0, bytes[j].0
            );
        }
    }
}
