//! Bounded player I/O and server-owned effect scheduling.
use crate::{
    cmus,
    config::Config,
    effects::{Player, Snapshot, Source, View},
    mpv,
    server::{ApiError, App, failed},
};
use anyhow::{Context, Result};
use axum::{Json, extract::State, http::StatusCode};
use serde::Deserialize;
use serde_json::json;
use std::{
    sync::Arc,
    time::{Duration, Instant},
};

pub async fn snapshot(config: &Config, source: Source) -> Result<Snapshot> {
    match source {
        Source::Local => {
            let raw = cmus::command(&config.cmus_socket, "status", config.timeout()).await?;
            let s = cmus::parse(&raw)?;
            let track = std::path::Path::new(&s.file)
                .strip_prefix(&config.music_root)
                .ok()
                .and_then(|p| p.to_str())
                .map(str::to_owned);
            Ok(Snapshot {
                track,
                position: s.position as f64,
                duration: s.duration as f64,
                playing: s.status == "playing",
                coarse: true,
            })
        }
        Source::Stream => {
            let stream = config.stream.as_ref().context("Stream not configured")?;
            let v = mpv::commands(
                &stream.mpv_socket,
                ["path", "time-pos", "duration", "pause", "core-idle"]
                    .into_iter()
                    .map(|p| json!(["get_property", p]))
                    .collect(),
                config.timeout(),
            )
            .await?;
            let track = v[0]
                .as_str()
                .and_then(|p| p.strip_prefix("https://music.youtube.com/watch?v="))
                .map(str::to_owned);
            Ok(Snapshot {
                track,
                position: v[1].as_f64().unwrap_or(0.0),
                duration: v[2].as_f64().unwrap_or(0.0),
                playing: v[3] == false && v[4] == false && v[1].is_number(),
                coarse: false,
            })
        }
    }
}

pub async fn volume(config: &Config, source: Source, value: u8) -> Result<()> {
    match source {
        Source::Local => {
            // Never change hardware/system mixer volume. CMUS persists software gain.
            cmus::command(&config.cmus_socket, "set softvol=true", config.timeout()).await?;
            cmus::command(
                &config.cmus_socket,
                &format!("vol {value}%"),
                config.timeout(),
            )
            .await?;
        }
        Source::Stream => {
            let stream = config.stream.as_ref().context("Stream not configured")?;
            mpv::commands(
                &stream.mpv_socket,
                vec![json!(["set_property", "volume", value])],
                config.timeout(),
            )
            .await?;
        }
    }
    Ok(())
}
async fn seek(config: &Config, source: Source, position: f64) -> Result<()> {
    match source {
        Source::Local => {
            cmus::command(
                &config.cmus_socket,
                &format!("seek {}", position.floor() as u64),
                config.timeout(),
            )
            .await?;
        }
        Source::Stream => {
            mpv::commands(
                &config
                    .stream
                    .as_ref()
                    .context("Stream not configured")?
                    .mpv_socket,
                vec![json!(["seek", position, "absolute+exact"])],
                config.timeout(),
            )
            .await?;
        }
    }
    Ok(())
}
async fn set_gain(config: &Config, source: Source, p: &mut Player, gain: u8) -> Result<()> {
    if p.volume != gain {
        volume(config, source, gain).await?;
        p.volume = gain;
    }
    Ok(())
}

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Action {
    Fade,
    Ab,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    source: Source,
    action: Action,
    track_id: Option<String>,
}

pub async fn control(
    State(app): State<Arc<App>>,
    Json(request): Json<Request>,
) -> Result<Json<View>, ApiError> {
    let _guard = app.controls.lock().await;
    let mut effects = app.effects.lock().await;
    let p = &mut effects[request.source.index()];
    let snapshot = snapshot(&app.config, request.source)
        .await
        .map_err(failed)?;
    p.observe(&snapshot);
    if snapshot.track.is_none() || snapshot.track != request.track_id || snapshot.duration <= 0.0 {
        return Err(ApiError(
            StatusCode::CONFLICT,
            "Select a track, or refresh playback before setting effects.",
        ));
    }
    p.error = None;
    p.retry_in = 0.0;
    let jump = match request.action {
        Action::Fade => {
            if p.b.is_some() {
                return Err(ApiError(
                    StatusCode::CONFLICT,
                    "Fade is required during AB looping.",
                ));
            }
            p.preference = !p.preference;
            // Enabling mid-track must not suddenly mute the current note.
            p.attack = app.config.fade_seconds;
            None
        }
        Action::Ab => p
            .mark(snapshot.position)
            .map_err(|e| ApiError(StatusCode::BAD_REQUEST, e))?,
    };
    let result = async {
        if let Some(position) = jump {
            if snapshot.playing {
                let (start, end) = p.range().expect("completed AB range");
                fade_down(
                    &app.config,
                    request.source,
                    p,
                    app.config.fade_seconds.min((end - start) / 3.0),
                )
                .await?;
            }
            set_gain(&app.config, request.source, p, 0).await?;
            seek(&app.config, request.source, position).await?;
        } else if !p.enabled() {
            set_gain(&app.config, request.source, p, 100).await?;
        }
        Ok::<(), anyhow::Error>(())
    }
    .await;
    if let Err(error) = result {
        recover(&app.config, request.source, p).await;
        return Err(failed(error));
    }
    Ok(Json(p.view()))
}

/// Called with the existing playback control lock, after track validation.
pub async fn transition(app: &App, source: Source) -> Result<()> {
    let mut effects = app.effects.lock().await;
    let p = &mut effects[source.index()];
    p.clear();
    if !p.preference {
        set_gain(&app.config, source, p, 100).await?;
        return Ok(());
    }
    let current = snapshot(&app.config, source).await?;
    let result = async {
        if current.playing {
            fade_down(&app.config, source, p, app.config.fade_seconds).await?;
        }
        set_gain(&app.config, source, p, 0).await
    }
    .await;
    if let Err(error) = result {
        recover(&app.config, source, p).await;
        return Err(error);
    }
    p.track = None;
    p.restart(0.0);
    Ok(())
}

/// Called only after a validated manual seek succeeds, under the control lock.
pub async fn manual_seek(app: &App, source: Source, position: f64) -> Result<()> {
    let mut effects = app.effects.lock().await;
    let p = &mut effects[source.index()];
    p.manual_seek(position);
    set_gain(&app.config, source, p, 100).await
}

/// Fade the outgoing source without losing its paused AB range.
pub async fn before_pause(app: &App, source: Source) -> Result<()> {
    let mut effects = app.effects.lock().await;
    let p = &mut effects[source.index()];
    if !p.enabled() {
        return Ok(());
    }
    let current = snapshot(&app.config, source).await?;
    if !current.playing {
        return Ok(());
    }
    let seconds = p
        .range()
        .map(|(a, b)| app.config.fade_seconds.min((b - a) / 3.0))
        .unwrap_or(app.config.fade_seconds);
    if let Err(error) = fade_down(&app.config, source, p, seconds).await {
        recover(&app.config, source, p).await;
        return Err(error);
    }
    p.restart(current.position);
    Ok(())
}

async fn fade_down(config: &Config, source: Source, p: &mut Player, seconds: f64) -> Result<()> {
    let start = Instant::now();
    let initial = p.volume;
    while start.elapsed().as_secs_f64() < seconds {
        let gain =
            (f64::from(initial) * (1.0 - start.elapsed().as_secs_f64() / seconds)).round() as u8;
        set_gain(config, source, p, gain).await?;
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    set_gain(config, source, p, 0).await
}

async fn recover(config: &Config, source: Source, p: &mut Player) {
    p.clear();
    p.preference = false;
    p.retry_in = 1.0;
    p.error = Some("Playback effects failed and were disabled. Check Portal logs.");
    if volume(config, source, 100).await.is_ok() {
        p.volume = 100;
    } else {
        eprintln!("Could not restore player volume after an effects error.");
    }
}

async fn tick(app: &App, dt: f64) {
    let Ok(_guard) = app.controls.try_lock() else {
        return;
    };
    let mut effects = app.effects.lock().await;
    for source in [Source::Local, Source::Stream] {
        let p = &mut effects[source.index()];
        if p.retry_in > 0.0 {
            p.retry_in = (p.retry_in - dt).max(0.0);
            continue;
        }
        if !p.needs_tick() {
            continue;
        }
        let result = async {
            let snapshot = snapshot(&app.config, source).await?;
            let (gain, jump) = p.tick(&snapshot, dt, app.config.fade_seconds);
            set_gain(&app.config, source, p, gain).await?;
            if let Some(position) = jump {
                seek(&app.config, source, position).await?;
            }
            Ok::<(), anyhow::Error>(())
        }
        .await;
        if result.is_err() {
            recover(&app.config, source, p).await;
        }
    }
}

pub async fn run(app: Arc<App>, mut stop: tokio::sync::watch::Receiver<bool>) {
    let mut interval = tokio::time::interval(Duration::from_millis(50));
    interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
    let mut previous = Instant::now();
    loop {
        tokio::select! {
            _=stop.changed()=>break,
            _=interval.tick()=>{ let now=Instant::now(); let dt=now.duration_since(previous).as_secs_f64().min(0.2); previous=now; tick(&app,dt).await; }
        }
    }
    if restore(&app.config).await.is_err() {
        eprintln!("Effects shutdown could not restore all player volumes.");
    }
}

/// Recover persisted CMUS software gain after a crash, and restore on clean exit.
pub async fn restore(config: &Config) -> Result<()> {
    let mut success = true;
    for source in [Source::Local, Source::Stream] {
        let socket = match source {
            Source::Local => &config.cmus_socket,
            Source::Stream => match &config.stream {
                Some(s) => &s.mpv_socket,
                None => continue,
            },
        };
        match mpv::available(socket).await {
            Ok(false) => {}
            Ok(true) => {
                if volume(config, source, 100).await.is_err() {
                    success = false;
                    eprintln!("Could not restore player software volume to 100%.");
                }
            }
            Err(_) => {
                success = false;
                eprintln!("Could not inspect player socket for volume recovery.");
            }
        }
    }
    anyhow::ensure!(success, "Player volume recovery failed");
    Ok(())
}

#[cfg(test)]
#[path = "effects_io_tests.rs"]
mod tests;
