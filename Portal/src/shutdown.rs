//! Stop playback reused outside Portal's managed services, without killing processes.
use crate::{cmus, config::Config, mpv, server};
use anyhow::{Context, Result};
use serde_json::json;
use std::{io::ErrorKind, path::Path, time::Duration};

async fn stop_cmus(path: &Path, timeout: Duration) -> Result<()> {
    match cmus::command(path, "player-stop", timeout).await {
        Ok(_) => Ok(()),
        Err(error)
            if error.downcast_ref::<std::io::Error>().is_some_and(|io| {
                matches!(
                    io.kind(),
                    ErrorKind::NotFound | ErrorKind::ConnectionRefused
                )
            }) =>
        {
            Ok(())
        }
        Err(error) => Err(error),
    }
}

async fn stop_stream(config: &Config) -> Result<()> {
    if let Some(stream) = &config.stream
        && mpv::available(&stream.mpv_socket).await?
    {
        mpv::commands(&stream.mpv_socket, vec![json!(["stop"])], config.timeout()).await?;
    }
    Ok(())
}

pub async fn run(config: &Config) -> Result<()> {
    // Attempt every player even when one fails. No service starts or network/auth requests.
    let (local, stream, tui) = tokio::join!(
        stop_cmus(&config.cmus_socket, config.timeout()),
        async {
            tokio::time::timeout(config.timeout(), stop_stream(config))
                .await
                .context("Stream stop timed out")?
        },
        server::pause_stream(config.timeout()),
    );
    let mut failed = false;
    for (name, result) in [("CMUS", local), ("Stream", stream), ("YTM TUI", tui)] {
        if result.is_err() {
            // Do not expose private config or raw IPC responses.
            eprintln!("Could not confirm {name} playback stopped.");
            failed = true;
        }
    }
    anyhow::ensure!(
        !failed,
        "Some players could not be stopped; check portal status/logs."
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

    #[tokio::test]
    async fn configured_stream_receives_stop_without_auth_or_library_access() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("mpv");
        let listener = tokio::net::UnixListener::bind(&path).unwrap();
        let config: Config = serde_json::from_value(json!({
            "listen":"127.0.0.1:8787", "music_root":"/unmounted-library",
            "cmus_socket":"/unused", "public_origin":"https://example.test",
            "allowed_login":"owner", "request_timeout_seconds":1,
            "stream":{"auth_file":"/absent-auth", "mpv_socket":path,
                "fetch_timeout_seconds":5, "list_limit":100}
        }))
        .unwrap();
        let worker = tokio::spawn(async move {
            let (probe, _) = listener.accept().await.unwrap();
            drop(probe);
            let (socket, _) = listener.accept().await.unwrap();
            let mut reader = BufReader::new(socket);
            let mut line = String::new();
            reader.read_line(&mut line).await.unwrap();
            let request: serde_json::Value = serde_json::from_str(&line).unwrap();
            assert_eq!(request["command"], json!(["stop"]));
            reader
                .get_mut()
                .write_all(b"{\"request_id\":0,\"error\":\"success\",\"data\":null}\n")
                .await
                .unwrap();
        });
        stop_stream(&config).await.unwrap();
        worker.await.unwrap();
    }

    #[tokio::test]
    async fn absent_or_stale_cmus_is_already_stopped() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("cmus");
        stop_cmus(&path, Duration::from_secs(1)).await.unwrap();
        let listener = tokio::net::UnixListener::bind(&path).unwrap();
        drop(listener);
        stop_cmus(&path, Duration::from_secs(1)).await.unwrap();
    }

    #[tokio::test]
    async fn reused_cmus_gets_stop_and_rejection_is_not_hidden() {
        for (reply, success) in [("\n", true), ("error rejected\n\n", false)] {
            let tmp = tempfile::tempdir().unwrap();
            let path = tmp.path().join("custom-cmus-socket");
            let listener = tokio::net::UnixListener::bind(&path).unwrap();
            let worker = tokio::spawn(async move {
                let (socket, _) = listener.accept().await.unwrap();
                let mut reader = BufReader::new(socket);
                let mut line = String::new();
                reader.read_line(&mut line).await.unwrap();
                assert_eq!(line, "player-stop\n");
                reader.get_mut().write_all(reply.as_bytes()).await.unwrap();
            });
            assert_eq!(
                stop_cmus(&path, Duration::from_secs(1)).await.is_ok(),
                success
            );
            worker.await.unwrap();
        }
    }
}
