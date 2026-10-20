//! Account ratings. Credentials remain on the server; writes set an explicit state.
use crate::server::{ApiError, App};
use axum::{
    Json,
    extract::{Query, State},
    http::StatusCode,
};
use serde::{Deserialize, Serialize};
use std::{sync::Arc, time::Duration};
use ytmusic_api::InnerTubeClient;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TrackQuery {
    id: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RatingRequest {
    id: String,
    liked: bool,
}

#[derive(Serialize)]
pub struct Rating {
    id: String,
    liked: bool,
}

fn parse_status(status: Option<&str>) -> anyhow::Result<bool> {
    match status {
        Some("LIKE") => Ok(true),
        Some("INDIFFERENT" | "DISLIKE") => Ok(false),
        _ => anyhow::bail!("Unknown rating"),
    }
}

async fn request(app: &App, id: String, desired: Option<bool>) -> Result<Json<Rating>, ApiError> {
    if !crate::stream::valid_video(&id) {
        return Err(ApiError(StatusCode::BAD_REQUEST, "Invalid track ID."));
    }
    let config = app.config.stream.as_ref().ok_or(ApiError(
        StatusCode::SERVICE_UNAVAILABLE,
        "Stream is not configured on this computer.",
    ))?;
    let _permit = app.rating_requests.try_acquire().map_err(|_| {
        ApiError(
            StatusCode::TOO_MANY_REQUESTS,
            "Another rating request is pending. Please retry.",
        )
    })?;
    let result = tokio::time::timeout(Duration::from_secs(config.fetch_timeout_seconds), async {
        let client = InnerTubeClient::from_auth_path(&config.auth_file)?;
        // Serialize against Liked pagination, not playback. Invalidate even when
        // a write times out: its upstream outcome may be unknown.
        let _cache_guard = if let Some(liked) = desired {
            let mut cache = app.liked.lock().await;
            *cache = Default::default();
            client
                .rate_track(&id, if liked { "LIKE" } else { "INDIFFERENT" })
                .await?;
            Some(cache)
        } else {
            None
        };
        let status = client.get_like_status(&id).await?;
        let liked = parse_status(status.as_deref())?;
        if let Some(desired) = desired {
            anyhow::ensure!(liked == desired, "Rating not yet confirmed");
        }
        Ok::<bool, anyhow::Error>(liked)
    })
    .await
    .map_err(|_| {
        ApiError(
            StatusCode::GATEWAY_TIMEOUT,
            "Rating request timed out. Reload the rating before retrying.",
        )
    })?
    .map_err(|_| {
        ApiError(
            StatusCode::BAD_GATEWAY,
            "Could not confirm the YouTube Music rating. Retry, or run ytm -auth on the computer.",
        )
    })?;
    Ok(Json(Rating { id, liked: result }))
}

pub async fn get(
    State(app): State<Arc<App>>,
    Query(query): Query<TrackQuery>,
) -> Result<Json<Rating>, ApiError> {
    request(&app, query.id, None).await
}

pub async fn set(
    State(app): State<Arc<App>>,
    Json(body): Json<RatingRequest>,
) -> Result<Json<Rating>, ApiError> {
    request(&app, body.id, Some(body.liked)).await
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn unknown_is_not_unliked() {
        assert!(parse_status(Some("LIKE")).unwrap());
        assert!(!parse_status(Some("INDIFFERENT")).unwrap());
        assert!(!parse_status(Some("DISLIKE")).unwrap());
        assert!(parse_status(None).is_err());
        assert!(parse_status(Some("UNKNOWN")).is_err());
    }
    #[test]
    fn writes_require_explicit_boolean_and_reject_extra_fields() {
        assert!(
            serde_json::from_str::<RatingRequest>(r#"{"id":"abcdefghijk","liked":true}"#)
                .unwrap()
                .liked
        );
        for invalid in [
            r#"{"id":"abcdefghijk"}"#,
            r#"{"id":"abcdefghijk","liked":"true"}"#,
            r#"{"id":"abcdefghijk","liked":true,"url":"https://example.com"}"#,
        ] {
            assert!(serde_json::from_str::<RatingRequest>(invalid).is_err());
        }
    }
}
