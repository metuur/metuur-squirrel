use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime};
use url::Url;

#[derive(Debug, PartialEq)]
pub struct Target {
    pub project_id: String,
    pub task_id: Option<String>,
}

#[derive(Debug, PartialEq)]
pub enum DeepLinkError {
    UnknownScheme,
    UnknownHost,
    BadPath,
}

fn is_valid_segment(s: &str) -> bool {
    !s.is_empty() && s.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

/// Validates a deep-link URL against the squirrel:// scheme contract (R-3.4, R-3.5, R-3.6).
///
/// Accepted forms:
///   squirrel://projects/<project-id>
///   squirrel://projects/<project-id>/<task-id>
/// Each segment must match [A-Za-z0-9_-]+.
pub fn validate(url: &Url) -> Result<Target, DeepLinkError> {
    if url.scheme() != "squirrel" {
        return Err(DeepLinkError::UnknownScheme);
    }
    if url.host_str() != Some("projects") {
        return Err(DeepLinkError::UnknownHost);
    }
    let segments: Vec<&str> = url
        .path_segments()
        .map(|iter| iter.filter(|s| !s.is_empty()).collect())
        .unwrap_or_default();

    match segments.as_slice() {
        [proj] if is_valid_segment(proj) => Ok(Target {
            project_id: (*proj).to_string(),
            task_id: None,
        }),
        [proj, task] if is_valid_segment(proj) && is_valid_segment(task) => Ok(Target {
            project_id: (*proj).to_string(),
            task_id: Some((*task).to_string()),
        }),
        _ => Err(DeepLinkError::BadPath),
    }
}

#[derive(Clone, Serialize)]
struct FocusProjectPayload {
    #[serde(rename = "projectId")]
    project_id: String,
    #[serde(rename = "taskId")]
    task_id: Option<String>,
}

/// Foregrounds the popup window and emits `deep-link://focus-project` (R-4.1–R-4.7).
pub fn handle<R: Runtime>(app: &AppHandle<R>, url: &Url) {
    let t_start = std::time::Instant::now();

    let target = match validate(url) {
        Ok(t) => t,
        Err(DeepLinkError::UnknownScheme) => {
            tracing::warn!(tag = "deep-link-dropped", subtag = "deep-link-unknown-scheme", %url);
            return;
        }
        Err(DeepLinkError::UnknownHost) => {
            tracing::warn!(tag = "deep-link-dropped", subtag = "deep-link-unknown-host", %url);
            return;
        }
        Err(DeepLinkError::BadPath) => {
            tracing::warn!(tag = "deep-link-dropped", subtag = "deep-link-bad-path", %url);
            return;
        }
    };

    if let Some(window) = app.get_webview_window("main") {
        if let Err(e) = window.show() {
            tracing::warn!(error = %e, "deep-link: show window failed");
        }
        if let Err(e) = window.set_focus() {
            tracing::warn!(error = %e, "deep-link: focus window failed");
        }
    } else {
        tracing::warn!("deep-link: 'main' window not found");
    }

    let payload = FocusProjectPayload {
        project_id: target.project_id.clone(),
        task_id: target.task_id.clone(),
    };
    if let Err(e) = app.emit("deep-link://focus-project", payload) {
        tracing::warn!(error = %e, "deep-link: emit failed");
    }

    let elapsed_ms = t_start.elapsed().as_millis();
    tracing::info!(
        tag = "deep-link-handled",
        project_id = %target.project_id,
        task_id = ?target.task_id,
        elapsed_ms,
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(s: &str) -> Url {
        Url::parse(s).expect("test URL must be valid")
    }

    #[test]
    fn accept_project_only() {
        let t = validate(&parse("squirrel://projects/FOO")).unwrap();
        assert_eq!(t.project_id, "FOO");
        assert_eq!(t.task_id, None);
    }

    #[test]
    fn accept_project_and_task() {
        let t = validate(&parse("squirrel://projects/FOO/BAR")).unwrap();
        assert_eq!(t.project_id, "FOO");
        assert_eq!(t.task_id, Some("BAR".to_string()));
    }

    #[test]
    fn reject_wrong_scheme() {
        assert_eq!(validate(&parse("http://projects/FOO")), Err(DeepLinkError::UnknownScheme));
    }

    #[test]
    fn reject_wrong_host() {
        assert_eq!(validate(&parse("squirrel://focus/FOO")), Err(DeepLinkError::UnknownHost));
    }

    #[test]
    fn reject_empty_path() {
        assert_eq!(validate(&parse("squirrel://projects/")), Err(DeepLinkError::BadPath));
    }

    #[test]
    fn reject_three_segments() {
        assert_eq!(validate(&parse("squirrel://projects/FOO/BAR/BAZ")), Err(DeepLinkError::BadPath));
    }

    #[test]
    fn reject_space_in_project_id() {
        // spaces percent-encode to %20; is_valid_segment rejects the non-alphanumeric byte
        let url = Url::parse("squirrel://projects/FO%20O").unwrap();
        assert_eq!(validate(&url), Err(DeepLinkError::BadPath));
    }

    #[test]
    fn reject_space_in_task_id() {
        let url = Url::parse("squirrel://projects/FOO/B%20R").unwrap();
        assert_eq!(validate(&url), Err(DeepLinkError::BadPath));
    }
}
