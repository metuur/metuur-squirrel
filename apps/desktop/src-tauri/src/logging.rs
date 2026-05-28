use std::path::{Path, PathBuf};
use tracing_appender::non_blocking::{NonBlocking, WorkerGuard};
use tracing_subscriber::EnvFilter;

const LOG_FILE_NAME: &str = "squirrel.log";

pub fn squirrel_dir() -> PathBuf {
    dirs::home_dir()
        .expect("home directory must resolve on macOS")
        .join(".squirrel")
}

pub fn log_dir() -> PathBuf {
    squirrel_dir().join("logs")
}

/// Satisfies R-1.1: create `~/.squirrel/` if it does not exist. Called from
/// `lib::run()` before logging init so the rest of startup can assume the
/// config root exists. Idempotent.
pub fn ensure_squirrel_dir() -> std::io::Result<PathBuf> {
    ensure_dir_at(&squirrel_dir())
}

fn ensure_dir_at(dir: &Path) -> std::io::Result<PathBuf> {
    std::fs::create_dir_all(dir)?;
    Ok(dir.to_path_buf())
}

pub fn init() -> WorkerGuard {
    init_with_dir(&log_dir())
}

pub fn init_with_dir(dir: &Path) -> WorkerGuard {
    let (writer, guard) = file_writer(dir);
    // Default `SystemTime` timer emits RFC-3339 UTC timestamps, which satisfies
    // the "ISO-8601 timestamps" requirement without pulling in the `time` crate.
    let _ = tracing_subscriber::fmt()
        .with_writer(writer)
        .with_ansi(false)
        .with_target(true)
        .with_env_filter(env_filter())
        .try_init();
    guard
}

fn env_filter() -> EnvFilter {
    EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"))
}

fn file_writer(dir: &Path) -> (NonBlocking, WorkerGuard) {
    std::fs::create_dir_all(dir).expect("create ~/.squirrel/logs/");
    let appender = tracing_appender::rolling::never(dir, LOG_FILE_NAME);
    tracing_appender::non_blocking(appender)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use tracing::subscriber::with_default;

    fn read_log(dir: &Path) -> String {
        // Non-blocking appender flushes on a background thread; give it a beat.
        std::thread::sleep(Duration::from_millis(200));
        std::fs::read_to_string(dir.join(LOG_FILE_NAME)).unwrap_or_default()
    }

    fn scoped_subscriber(dir: &Path) -> (impl tracing::Subscriber + Send + Sync, WorkerGuard) {
        let (writer, guard) = file_writer(dir);
        let sub = tracing_subscriber::fmt()
            .with_writer(writer)
            .with_ansi(false)
            .with_target(true)
            .with_env_filter(EnvFilter::new("info"))
            .finish();
        (sub, guard)
    }

    #[test]
    fn creates_log_file_and_writes_iso8601_timestamped_line() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let (sub, _guard) = scoped_subscriber(tmp.path());
            with_default(sub, || {
                tracing::info!("test marker alpha");
            });
        }
        let contents = read_log(tmp.path());
        assert!(
            tmp.path().join(LOG_FILE_NAME).exists(),
            "log file must exist"
        );
        assert!(
            contents.contains("test marker alpha"),
            "log must contain message; got: {contents}"
        );
        let starts_with_year = contents
            .lines()
            .next()
            .map(|l| {
                l.len() >= 5
                    && l.chars().take(4).all(|c| c.is_ascii_digit())
                    && l.as_bytes()[4] == b'-'
            })
            .unwrap_or(false);
        assert!(
            starts_with_year,
            "first line must start with ISO-8601 timestamp; got: {contents}"
        );
    }

    #[test]
    fn appends_across_runs_without_truncating() {
        let tmp = tempfile::tempdir().unwrap();
        {
            let (sub, _g1) = scoped_subscriber(tmp.path());
            with_default(sub, || {
                tracing::info!("first run line");
            });
        }
        std::thread::sleep(Duration::from_millis(150));
        {
            let (sub, _g2) = scoped_subscriber(tmp.path());
            with_default(sub, || {
                tracing::info!("second run line");
            });
        }
        let contents = read_log(tmp.path());
        assert!(
            contents.contains("first run line"),
            "must retain first run: {contents}"
        );
        assert!(
            contents.contains("second run line"),
            "must contain second run: {contents}"
        );
    }

    #[test]
    fn creates_directory_tree_if_missing() {
        let tmp = tempfile::tempdir().unwrap();
        let nested = tmp.path().join("does/not/exist/yet/logs");
        assert!(!nested.exists());
        let (_writer, _guard) = file_writer(&nested);
        assert!(nested.exists(), "init must create the full path");
    }

    #[test]
    fn ensure_dir_at_creates_when_missing() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("fake-home/.squirrel");
        assert!(!target.exists());
        let result = ensure_dir_at(&target).expect("must succeed");
        assert_eq!(result, target);
        assert!(target.exists(), "directory must be created");
        assert!(target.is_dir(), "result must be a directory");
    }

    #[test]
    fn ensure_dir_at_is_idempotent_when_already_present() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("already-exists");
        std::fs::create_dir_all(&target).unwrap();
        // Calling twice in a row must not error.
        ensure_dir_at(&target).expect("first call");
        ensure_dir_at(&target).expect("second call must not error on existing dir");
        assert!(target.exists());
    }
}
