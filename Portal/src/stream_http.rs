use crate::{
    cmus,
    config::StreamConfig,
    mpv,
    server::{self, ApiError, App},
    stream,
};
use axum::{
    Json,
    extract::{Query, State},
    http::StatusCode,
};
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;

fn config(app: &App) -> Result<&StreamConfig, ApiError> {
    app.config.stream.as_ref().ok_or(ApiError(
        StatusCode::SERVICE_UNAVAILABLE,
        "Stream is not configured on this computer.",
    ))
}
fn unavailable(error: anyhow::Error) -> ApiError {
    if error.is::<crate::stream::Expired>() {
        return ApiError(
            StatusCode::CONFLICT,
            "Stream continuation expired; reconnect pagination.",
        );
    }
    // Never log auth objects or upstream response bodies.
    ApiError(
        StatusCode::BAD_GATEWAY,
        "YouTube Music request failed. Check the network or run ytm -auth on the computer, then Refresh.",
    )
}

pub async fn browse(
    State(app): State<Arc<App>>,
    Query(query): Query<stream::Browse>,
) -> Result<Json<stream::Page>, ApiError> {
    let config = config(&app)?;
    let _permit = app.stream_fetch.try_acquire().map_err(|_| {
        ApiError(
            StatusCode::TOO_MANY_REQUESTS,
            "Another Stream list is loading. Please try again shortly.",
        )
    })?;
    let (page, tracks) = tokio::time::timeout(
        std::time::Duration::from_secs(config.fetch_timeout_seconds),
        async {
            if matches!(query.view.as_str(), "liked" | "playlist") {
                let mut cache = app.liked.lock().await;
                crate::liked::browse(config, &query, &mut cache).await
            } else if query.view == "recommended" {
                let mut cache = app.home.lock().await;
                crate::home::browse(config, &query, &mut cache).await
            } else {
                stream::browse(config, &query).await
            }
        },
    )
    .await
    .map_err(|_| {
        ApiError(
            StatusCode::GATEWAY_TIMEOUT,
            "YouTube Music took too long. Please retry.",
        )
    })?
    .map_err(unavailable)?;
    let mut state = app.stream.lock().await;
    if state.catalog.len() + tracks.len() > 10000 {
        state.catalog.clear();
    }
    for track in tracks {
        state.catalog.insert(track.id.clone(), track);
    }
    Ok(Json(page))
}

pub async fn status(State(app): State<Arc<App>>) -> Result<Json<stream::Status>, ApiError> {
    let config = config(&app)?;
    let state = app.stream.lock().await;
    let mut result = stream::status(config, &state, app.config.timeout())
        .await
        .map_err(server::failed)?;
    result.effects = app.effects.lock().await[1].view();
    Ok(Json(result))
}

#[derive(Deserialize)]
#[serde(tag = "action", rename_all = "snake_case", deny_unknown_fields)]
pub enum Control {
    Play {
        ids: Vec<String>,
        index: usize,
        #[serde(default)]
        metadata: Vec<crate::library::Track>,
    },
    Toggle {},
    Previous {},
    Next {},
    Backward {},
    Forward {},
    Seek {
        seconds: u64,
    },
    Repeat {},
    Shuffle {},
}

async fn pause_other_players(app: &App) -> anyhow::Result<()> {
    server::pause_stream(app.config.timeout()).await?;
    match tokio::net::UnixStream::connect(&app.config.cmus_socket).await {
        Ok(_) => {
            let raw =
                cmus::command(&app.config.cmus_socket, "status", app.config.timeout()).await?;
            if cmus::parse(&raw)?.status == "playing" {
                crate::effects_io::before_pause(app, crate::effects::Source::Local).await?;
                cmus::command(
                    &app.config.cmus_socket,
                    "player-pause",
                    app.config.timeout(),
                )
                .await?;
            }
        }
        Err(e)
            if matches!(
                e.kind(),
                std::io::ErrorKind::NotFound | std::io::ErrorKind::ConnectionRefused
            ) => {}
        Err(e) => return Err(e.into()),
    }
    Ok(())
}

async fn ensure_player(app: &App, config: &StreamConfig) -> anyhow::Result<()> {
    if mpv::available(&config.mpv_socket).await? {
        return Ok(());
    }
    let output = tokio::time::timeout(
        app.config.timeout(),
        tokio::process::Command::new("systemctl")
            .args(["--user", "start", "portal-stream.service"])
            .kill_on_drop(true)
            .output(),
    )
    .await??;
    anyhow::ensure!(
        output.status.success(),
        "Could not start portal-stream.service"
    );
    for _ in 0..20 {
        if mpv::available(&config.mpv_socket).await? {
            return Ok(());
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
    anyhow::bail!("Stream player did not become ready")
}

pub async fn control(
    State(app): State<Arc<App>>,
    Json(control): Json<Control>,
) -> Result<Json<stream::Status>, ApiError> {
    let _guard = app.controls.lock().await;
    let config = config(&app)?;
    let mut state = app.stream.lock().await;
    // Validate before starting services, pausing music or replacing a queue.
    let selected = if let Control::Play {
        ids,
        index,
        metadata,
    } = &control
    {
        Some(stream::queue(&state, ids, *index, metadata).map_err(|_| {
            ApiError(
                StatusCode::BAD_REQUEST,
                "Invalid queue selection or metadata.",
            )
        })?)
    } else {
        None
    };
    ensure_player(&app, config).await.map_err(server::failed)?;
    let current = stream::status(config, &state, app.config.timeout())
        .await
        .map_err(server::failed)?;
    let manual_position = match &control {
        Control::Seek { seconds } => Some(*seconds),
        Control::Backward {} => Some(current.position.saturating_sub(5)),
        Control::Forward {} => Some(current.position.saturating_add(5).min(current.duration)),
        _ => None,
    };
    if matches!(control, Control::Next {} | Control::Previous {}) && current.status == "stopped" {
        return Err(ApiError(
            StatusCode::CONFLICT,
            "Select a Stream track first.",
        ));
    }
    if matches!(
        control,
        Control::Play { .. } | Control::Next {} | Control::Previous {}
    ) {
        crate::effects_io::transition(&app, crate::effects::Source::Stream)
            .await
            .map_err(server::failed)?;
    }
    if let (Control::Play { index, .. }, Some(tracks)) = (&control, selected) {
        pause_other_players(&app).await.map_err(server::failed)?;
        stream::load(
            config,
            &tracks,
            *index,
            current.shuffle,
            app.config.timeout(),
        )
        .await
        .map_err(server::failed)?;
        state.queue = tracks;
    } else {
        if (matches!(control, Control::Toggle {}) && current.status != "playing")
            || matches!(control, Control::Next {} | Control::Previous {})
        {
            if current.status == "stopped" {
                return Err(ApiError(
                    StatusCode::CONFLICT,
                    "Select a Stream track first.",
                ));
            }
            pause_other_players(&app).await.map_err(server::failed)?;
        }
        let resume = matches!(control, Control::Next {} | Control::Previous {});
        let mut commands = playback_commands(control, &current)?;
        if resume {
            commands.push(json!(["set_property", "pause", false]));
        }
        mpv::commands(&config.mpv_socket, commands, app.config.timeout())
            .await
            .map_err(server::failed)?;
    }
    if let Some(position) = manual_position {
        crate::effects_io::manual_seek(&app, crate::effects::Source::Stream, position as f64)
            .await
            .map_err(server::failed)?;
    }
    let mut result = stream::status(config, &state, app.config.timeout())
        .await
        .map_err(server::failed)?;
    result.effects = app.effects.lock().await[1].view();
    Ok(Json(result))
}

fn playback_commands(
    control: Control,
    current: &stream::Status,
) -> Result<Vec<serde_json::Value>, ApiError> {
    Ok(match control {
        Control::Toggle {} => vec![json!(["cycle", "pause"])],
        Control::Previous {} if current.position > 3 => vec![json!(["seek", 0, "absolute"])],
        Control::Previous {} => vec![json!(["playlist-prev", "weak"])],
        Control::Next {} => vec![json!(["playlist-next", "weak"])],
        Control::Backward {} => vec![json!(["seek", -5, "relative"])],
        Control::Forward {} => vec![json!(["seek", 5, "relative"])],
        Control::Seek { seconds } => {
            if seconds > current.duration {
                return Err(ApiError(
                    StatusCode::BAD_REQUEST,
                    "Position exceeds track duration.",
                ));
            }
            vec![json!(["seek", seconds, "absolute+exact"])]
        }
        Control::Shuffle {} => vec![
            json!([if current.shuffle {
                "playlist-unshuffle"
            } else {
                "playlist-shuffle"
            }]),
            json!(["set_property", "shuffle", !current.shuffle]),
        ],
        Control::Repeat {} => {
            let (file, list) = match current.repeat {
                "one" => ("no", "inf"),
                "all" => ("no", "no"),
                _ => ("inf", "no"),
            };
            vec![
                json!(["set_property", "loop-file", file]),
                json!(["set_property", "loop-playlist", list]),
            ]
        }
        Control::Play { .. } => unreachable!(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn status() -> stream::Status {
        stream::Status {
            effects: Default::default(),
            status: "paused",
            title: String::new(),
            artist: String::new(),
            album: String::new(),
            track_id: None,
            position: 12,
            duration: 100,
            repeat: "one",
            shuffle: false,
            error: None,
        }
    }
    #[test]
    fn controls_reject_out_of_range_seek_and_unknown_actions() {
        assert!(playback_commands(Control::Seek { seconds: 101 }, &status()).is_err());
        assert!(
            serde_json::from_value::<Control>(json!({"action":"run","command":"quit"})).is_err()
        );
        assert!(
            serde_json::from_value::<Control>(json!({"action":"toggle","command":"quit"})).is_err()
        );
    }
    #[test]
    fn shuffle_toggles_queue_order_and_player_owned_state() {
        let mut current = status();
        assert_eq!(
            playback_commands(Control::Shuffle {}, &current).ok(),
            Some(vec![
                json!(["playlist-shuffle"]),
                json!(["set_property", "shuffle", true])
            ])
        );
        current.shuffle = true;
        assert_eq!(
            playback_commands(Control::Shuffle {}, &current).ok(),
            Some(vec![
                json!(["playlist-unshuffle"]),
                json!(["set_property", "shuffle", false])
            ])
        );
    }

    #[test]
    fn previous_restarts_and_repeat_cycles() {
        assert_eq!(
            playback_commands(Control::Previous {}, &status()).ok(),
            Some(vec![json!(["seek", 0, "absolute"])])
        );
        assert_eq!(
            playback_commands(Control::Repeat {}, &status()).ok(),
            Some(vec![
                json!(["set_property", "loop-file", "no"]),
                json!(["set_property", "loop-playlist", "inf"])
            ])
        );
    }
}
