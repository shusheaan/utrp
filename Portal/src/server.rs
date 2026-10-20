use crate::{
    cmus,
    config::Config,
    library::{self, Track},
};
use axum::{
    Json, Router,
    extract::{DefaultBodyLimit, Request, State},
    http::{HeaderMap, HeaderValue, Method, StatusCode},
    middleware::{self, Next},
    response::{Html, IntoResponse, Response},
    routing::{get, post},
};
use serde::Deserialize;
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct App {
    pub effects: Mutex<[crate::effects::Player; 2]>,
    pub stream: Mutex<crate::stream::StreamState>,
    pub stream_fetch: tokio::sync::Semaphore,
    pub rating_requests: tokio::sync::Semaphore,
    pub liked: Mutex<crate::liked::Cache>,
    pub home: Mutex<crate::home::Cache>,
    pub config: Config,
    pub tracks: Vec<Track>,
    pub controls: Mutex<()>,
}

pub struct ApiError(pub(crate) StatusCode, pub(crate) &'static str);
impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(serde_json::json!({"error": self.1}))).into_response()
    }
}

pub(crate) fn failed(error: anyhow::Error) -> ApiError {
    eprintln!("Portal backend: {error:#}");
    ApiError(
        StatusCode::SERVICE_UNAVAILABLE,
        "Playback control failed. Please retry or check portal status.",
    )
}

pub fn router(app: Arc<App>) -> Router {
    Router::new()
        .route(
            "/",
            get(|| async { Html(include_str!("../web/index.html")) }),
        )
        .route(
            "/app.js",
            get(|| async {
                (
                    [("content-type", "text/javascript; charset=utf-8")],
                    include_str!("../web/app.js"),
                )
            }),
        )
        .route(
            "/style.css",
            get(|| async {
                (
                    [("content-type", "text/css; charset=utf-8")],
                    include_str!("../web/style.css"),
                )
            }),
        )
        .route("/api/stream/browse", get(crate::stream_http::browse))
        .route(
            "/api/stream/like",
            get(crate::ratings::get).post(crate::ratings::set),
        )
        .route("/api/stream/status", get(crate::stream_http::status))
        .route("/api/stream/control", post(crate::stream_http::control))
        .route("/api/library", get(library_handler))
        .route("/api/status", get(status_handler))
        .route("/api/control", post(control_handler))
        .route("/api/effects", post(crate::effects_io::control))
        .layer(DefaultBodyLimit::max(16384))
        .layer(middleware::from_fn_with_state(Arc::clone(&app), security))
        .with_state(app)
}

fn header<'a>(headers: &'a HeaderMap, name: &str) -> Option<&'a str> {
    headers.get(name).and_then(|value| value.to_str().ok())
}

pub fn authorized(config: &Config, method: &Method, headers: &HeaderMap) -> bool {
    let authority = config.public_origin.trim_start_matches("https://");
    let local = config.listen.to_string();
    let host = header(headers, "host");
    if host != Some(authority) && host != Some(local.as_str()) {
        return false;
    }
    // Serve overwrites identity headers. The backend never binds a LAN interface.
    if header(headers, "tailscale-user-login") != Some(config.allowed_login.as_str()) {
        return false;
    }
    if header(headers, "sec-fetch-site") == Some("cross-site") {
        return false;
    }
    if method != Method::GET && method != Method::HEAD {
        let origin = header(headers, "origin");
        if origin != Some(config.public_origin.as_str())
            && origin != Some(format!("http://{local}").as_str())
        {
            return false;
        }
        if header(headers, "x-portal-request") != Some("1") {
            return false;
        }
    }
    true
}

async fn security(State(app): State<Arc<App>>, request: Request, next: Next) -> Response {
    let mut response = if authorized(&app.config, request.method(), request.headers()) {
        next.run(request).await
    } else {
        ApiError(
            StatusCode::FORBIDDEN,
            "Open Portal through your own Tailscale HTTPS address.",
        )
        .into_response()
    };
    for (name, value) in [
        ("cache-control", "no-store"),
        ("x-content-type-options", "nosniff"),
        ("referrer-policy", "no-referrer"),
        ("x-frame-options", "DENY"),
        (
            "content-security-policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        ),
    ] {
        response
            .headers_mut()
            .insert(name, HeaderValue::from_static(value));
    }
    response
}

async fn library_handler(State(app): State<Arc<App>>) -> Json<Vec<Track>> {
    Json(app.tracks.clone())
}

async fn get_status(app: &App) -> Result<cmus::Status, ApiError> {
    let raw = cmus::command(&app.config.cmus_socket, "status", app.config.timeout())
        .await
        .map_err(failed)?;
    let mut status = cmus::parse(&raw).map_err(failed)?;
    status.track_id = std::path::Path::new(&status.file)
        .strip_prefix(&app.config.music_root)
        .ok()
        .and_then(|path| path.to_str())
        .map(str::to_owned);
    status.effects = app.effects.lock().await[0].view();
    Ok(status)
}

async fn status_handler(State(app): State<Arc<App>>) -> Result<Json<cmus::Status>, ApiError> {
    Ok(Json(get_status(&app).await?))
}

#[derive(Deserialize)]
#[serde(tag = "action", rename_all = "snake_case", deny_unknown_fields)]
enum Control {
    Play { id: String },
    Toggle {},
    Previous {},
    Next {},
    Backward {},
    Forward {},
    Seek { seconds: u64 },
    Repeat {},
    Shuffle {},
}

async fn send(app: &App, command: &str) -> Result<(), ApiError> {
    cmus::command(&app.config.cmus_socket, command, app.config.timeout())
        .await
        .map_err(failed)?;
    Ok(())
}

async fn pause_all_stream(app: &App) -> Result<(), ApiError> {
    pause_stream(app.config.timeout()).await.map_err(failed)?;
    if let Some(config) = &app.config.stream {
        if crate::mpv::available(&config.mpv_socket)
            .await
            .map_err(failed)?
        {
            crate::effects_io::before_pause(app, crate::effects::Source::Stream)
                .await
                .map_err(failed)?;
        }
        crate::mpv::pause_if_running(&config.mpv_socket, app.config.timeout())
            .await
            .map_err(failed)?;
    }
    Ok(())
}

async fn play(app: &App, id: &str) -> Result<(), ApiError> {
    let path = library::resolve(&app.config.music_root, &app.tracks, id).map_err(|_| {
        ApiError(
            StatusCode::BAD_REQUEST,
            "Track unavailable. Restart Portal to refresh the library.",
        )
    })?;
    crate::effects_io::transition(app, crate::effects::Source::Local)
        .await
        .map_err(failed)?;
    pause_all_stream(app).await?;
    send(app, &format!("player-play {}", path.display())).await
}

async fn control_handler(
    State(app): State<Arc<App>>,
    Json(control): Json<Control>,
) -> Result<Json<cmus::Status>, ApiError> {
    let _guard = app.controls.lock().await;
    ensure_cmus(&app).await.map_err(failed)?;
    let status = get_status(&app).await?;
    let manual_position = match &control {
        Control::Seek { seconds } => Some(*seconds),
        Control::Backward {} => Some(status.position.saturating_sub(5)),
        Control::Forward {} => Some(status.position.saturating_add(5).min(status.duration)),
        _ => None,
    };
    match control {
        Control::Play { id } => play(&app, &id).await?,
        Control::Toggle {} => {
            if status.status != "playing" {
                pause_all_stream(&app).await?;
            }
            send(
                &app,
                if status.status == "stopped" {
                    "player-play"
                } else {
                    "player-pause"
                },
            )
            .await?;
        }
        Control::Backward {} => send(&app, "seek -5").await?,
        Control::Forward {} => send(&app, "seek +5").await?,
        Control::Seek { seconds } => {
            if seconds > status.duration {
                return Err(ApiError(
                    StatusCode::BAD_REQUEST,
                    "Position exceeds track duration.",
                ));
            }
            send(&app, &format!("seek {seconds}")).await?;
        }
        Control::Next {} | Control::Previous {} if status.shuffle => {
            crate::effects_io::transition(&app, crate::effects::Source::Local)
                .await
                .map_err(failed)?;
            pause_all_stream(&app).await?;
            let previous = matches!(control, Control::Previous {});
            send(
                &app,
                if previous && status.position > 3 {
                    "seek 0"
                } else if previous {
                    "player-prev"
                } else {
                    "player-next"
                },
            )
            .await?;
        }
        Control::Next {} | Control::Previous {} => {
            let index = app
                .tracks
                .iter()
                .position(|track| Some(&track.id) == status.track_id.as_ref())
                .ok_or(ApiError(
                    StatusCode::CONFLICT,
                    "Select a track from the Local library first.",
                ))?;
            if let Some(next) = cmus::neighbour(
                index,
                app.tracks.len(),
                matches!(control, Control::Previous {}),
                status.position,
            ) {
                play(&app, &app.tracks[next].id).await?;
            }
        }
        Control::Shuffle {} => {
            send(
                &app,
                if status.shuffle {
                    "set shuffle=off"
                } else {
                    "set shuffle=tracks"
                },
            )
            .await?;
        }
        Control::Repeat {} => {
            let (all, one) = match status.repeat.as_str() {
                "one" => (true, false),
                "all" => (false, false),
                _ => (false, true),
            };
            send(&app, &format!("set repeat={all}")).await?;
            send(&app, &format!("set repeat_current={one}")).await?;
        }
    }
    if let Some(position) = manual_position {
        crate::effects_io::manual_seek(&app, crate::effects::Source::Local, position as f64)
            .await
            .map_err(failed)?;
    }
    Ok(Json(get_status(&app).await?))
}

async fn ensure_cmus(app: &App) -> anyhow::Result<()> {
    match tokio::net::UnixStream::connect(&app.config.cmus_socket).await {
        Ok(_) => return Ok(()),
        Err(error)
            if matches!(
                error.kind(),
                std::io::ErrorKind::NotFound | std::io::ErrorKind::ConnectionRefused
            ) => {}
        Err(error) => return Err(error.into()),
    }
    let output = tokio::time::timeout(
        app.config.timeout(),
        tokio::process::Command::new("systemctl")
            .args(["--user", "start", "portal-cmus.service"])
            .kill_on_drop(true)
            .output(),
    )
    .await??;
    anyhow::ensure!(
        output.status.success(),
        "Could not start portal-cmus.service"
    );
    for _ in 0..20 {
        if tokio::net::UnixStream::connect(&app.config.cmus_socket)
            .await
            .is_ok()
        {
            return Ok(());
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
    anyhow::bail!("CMUS did not become ready")
}

pub(crate) async fn pause_stream(timeout: std::time::Duration) -> anyhow::Result<()> {
    let output = tokio::time::timeout(
        timeout,
        tokio::process::Command::new("busctl")
            .args(["--user", "--no-legend", "list"])
            .kill_on_drop(true)
            .output(),
    )
    .await??;
    anyhow::ensure!(output.status.success(), "Could not inspect media players");
    let names = String::from_utf8(output.stdout)?;
    if names
        .lines()
        .any(|line| line.split_whitespace().next() == Some("org.mpris.MediaPlayer2.ytmusic-tui"))
    {
        let output = tokio::time::timeout(
            timeout,
            tokio::process::Command::new("busctl")
                .args([
                    "--user",
                    "call",
                    "org.mpris.MediaPlayer2.ytmusic-tui",
                    "/org/mpris/MediaPlayer2",
                    "org.mpris.MediaPlayer2.Player",
                    "Pause",
                ])
                .kill_on_drop(true)
                .output(),
        )
        .await??;
        anyhow::ensure!(
            output.status.success(),
            "Could not pause YTM; refusing overlapping playback"
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tower::ServiceExt;

    fn config() -> Config {
        Config {
            fade_seconds: 2.5,
            stream: None,
            listen: "127.0.0.1:8787".parse().unwrap(),
            music_root: "/music".into(),
            cmus_socket: "/tmp/nonexistent-cmus".into(),
            public_origin: "https://music.example:8443".into(),
            allowed_login: "owner@example".into(),
            request_timeout_seconds: 2,
        }
    }

    #[test]
    fn rejects_missing_identity_cross_origin_and_foreign_hosts() {
        let mut headers = HeaderMap::new();
        headers.insert("host", "music.example:8443".parse().unwrap());
        assert!(!authorized(&config(), &Method::GET, &headers));
        headers.insert("tailscale-user-login", "owner@example".parse().unwrap());
        assert!(authorized(&config(), &Method::GET, &headers));
        assert!(!authorized(&config(), &Method::POST, &headers));
        headers.insert("origin", "https://music.example:8443".parse().unwrap());
        headers.insert("x-portal-request", "1".parse().unwrap());
        assert!(authorized(&config(), &Method::POST, &headers));
        headers.insert("origin", "https://evil.example".parse().unwrap());
        assert!(!authorized(&config(), &Method::POST, &headers));
        headers.insert("host", "evil.example".parse().unwrap());
        assert!(!authorized(&config(), &Method::GET, &headers));
    }

    #[tokio::test]
    async fn http_gate_and_action_validation() {
        let app = router(Arc::new(App {
            effects: Mutex::new(Default::default()),
            stream: Mutex::new(crate::stream::StreamState::default()),
            stream_fetch: tokio::sync::Semaphore::new(1),
            rating_requests: tokio::sync::Semaphore::new(1),
            liked: Mutex::new(crate::liked::Cache::default()),
            home: Mutex::new(crate::home::Cache::default()),
            config: config(),
            tracks: vec![],
            controls: Mutex::new(()),
        }));
        let denied = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri("/api/library")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(denied.status(), StatusCode::FORBIDDEN);
        for (method, path, body, origin, expected) in [
            (
                "POST",
                "/api/effects",
                r#"{"source":"local","action":"fade"}"#,
                "https://evil.example",
                StatusCode::FORBIDDEN,
            ),
            (
                "POST",
                "/api/effects",
                r#"{"source":"local","action":"ab","command":"quit"}"#,
                "https://music.example:8443",
                StatusCode::UNPROCESSABLE_ENTITY,
            ),
            (
                "POST",
                "/api/effects",
                r#"{"source":"system","action":"fade"}"#,
                "https://music.example:8443",
                StatusCode::UNPROCESSABLE_ENTITY,
            ),
            (
                "GET",
                "/api/stream/like?id=bad",
                "",
                "https://music.example:8443",
                StatusCode::BAD_REQUEST,
            ),
            (
                "GET",
                "/api/stream/like?id=abcdefghijk",
                "",
                "https://music.example:8443",
                StatusCode::SERVICE_UNAVAILABLE,
            ),
            (
                "POST",
                "/api/stream/like",
                r#"{"id":"bad","liked":true}"#,
                "https://music.example:8443",
                StatusCode::BAD_REQUEST,
            ),
            (
                "POST",
                "/api/stream/like",
                r#"{"id":"abcdefghijk","liked":true}"#,
                "https://evil.example",
                StatusCode::FORBIDDEN,
            ),
            (
                "POST",
                "/api/stream/like",
                r#"{"id":"abcdefghijk","liked":true,"url":"evil"}"#,
                "https://music.example:8443",
                StatusCode::UNPROCESSABLE_ENTITY,
            ),
        ] {
            let response = app
                .clone()
                .oneshot(
                    Request::builder()
                        .method(method)
                        .uri(path)
                        .header("host", "music.example:8443")
                        .header("tailscale-user-login", "owner@example")
                        .header("origin", origin)
                        .header("x-portal-request", "1")
                        .header("content-type", "application/json")
                        .body(axum::body::Body::from(body))
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(response.status(), expected);
        }
        let allowed = app
            .oneshot(
                Request::builder()
                    .uri("/api/library")
                    .header("host", "music.example:8443")
                    .header("tailscale-user-login", "owner@example")
                    .body(axum::body::Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(allowed.status(), StatusCode::OK);
        assert_eq!(allowed.headers()["cache-control"], "no-store");
        assert!(serde_json::from_str::<Control>(r#"{"action":"shell","command":"id"}"#).is_err());
        assert!(
            serde_json::from_str::<Control>(r#"{"action":"play","id":"x","command":"id"}"#)
                .is_err()
        );
    }

    #[test]
    fn public_network_bind_is_forbidden() {
        let mut value = config();
        assert!(value.validate().is_ok());
        value.listen = "0.0.0.0:8787".parse().unwrap();
        assert!(value.validate().is_err());
    }
}
