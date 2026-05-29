#![allow(dead_code)]

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
