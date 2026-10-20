mod cmus;
mod config;
mod effects;
mod effects_io;
mod home;
mod home_parse;
mod library;
mod liked;
mod liked_parse;
mod mpv;
mod ratings;
mod server;
mod setup;
mod shutdown;
mod stream;
mod stream_catalog;
mod stream_http;

use anyhow::{Context, Result};
use std::{path::PathBuf, sync::Arc};

#[tokio::main]
async fn main() -> Result<()> {
    if std::env::args_os().nth(1).as_deref() == Some(std::ffi::OsStr::new("configure")) {
        let path = std::env::args_os()
            .nth(2)
            .map(PathBuf::from)
            .context("configure requires an output path")?;
        return setup::configure(&path);
    }
    let action = std::env::args_os().nth(1);
    if matches!(
        action.as_deref().and_then(|s| s.to_str()),
        Some("stop-playback" | "restore-volume")
    ) {
        let path = std::env::args_os()
            .nth(2)
            .map(PathBuf::from)
            .context("stop-playback requires a config path")?;
        // Shutdown must still work if the music library mount is unavailable.
        let config: config::Config = toml::from_str(&std::fs::read_to_string(path)?)?;
        config.validate()?;
        if action.as_deref() == Some(std::ffi::OsStr::new("restore-volume")) {
            return effects_io::restore(&config).await;
        }
        return shutdown::run(&config).await;
    }
    let path = std::env::args_os()
        .nth(1)
        .map(PathBuf::from)
        .context("Usage: utrp-portal /path/to/config.toml")?;
    let config = config::Config::load(&path)?;
    let tracks = library::scan(&config.music_root)?;
    let listener = tokio::net::TcpListener::bind(config.listen).await?;
    eprintln!(
        "Portal listening on {}; {} local tracks",
        config.listen,
        tracks.len()
    );
    effects_io::restore(&config).await?;
    let app = Arc::new(server::App {
        effects: tokio::sync::Mutex::new(Default::default()),
        stream: tokio::sync::Mutex::new(stream::StreamState::default()),
        stream_fetch: tokio::sync::Semaphore::new(1),
        rating_requests: tokio::sync::Semaphore::new(1),
        liked: tokio::sync::Mutex::new(liked::Cache::default()),
        home: tokio::sync::Mutex::new(home::Cache::default()),
        config,
        tracks,
        controls: tokio::sync::Mutex::new(()),
    });
    let (stop_tx, stop_rx) = tokio::sync::watch::channel(false);
    let worker = tokio::spawn(effects_io::run(Arc::clone(&app), stop_rx));
    let result = axum::serve(listener, server::router(Arc::clone(&app)))
        .with_graceful_shutdown(async {
            let mut term =
                tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
                    .expect("SIGTERM handler");
            tokio::select! { _=term.recv()=>{}, _=tokio::signal::ctrl_c()=>{} }
        })
        .await;
    let _ = stop_tx.send(true);
    worker.await?;
    result?;
    Ok(())
}
