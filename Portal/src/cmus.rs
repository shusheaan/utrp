use anyhow::{Context, Result, bail};
use serde::Serialize;
use std::{path::Path, time::Duration};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::UnixStream,
};

#[derive(Debug, Serialize)]
pub struct Status {
    pub effects: crate::effects::View,
    pub status: String,
    pub title: String,
    pub artist: String,
    pub album: String,
    pub position: u64,
    pub duration: u64,
    pub repeat: String,
    pub shuffle: bool,
    #[serde(skip)]
    pub file: String,
    pub track_id: Option<String>,
}

pub async fn command(socket: &Path, command: &str, timeout: Duration) -> Result<String> {
    if command.contains(['\n', '\r', '\0']) {
        bail!("Invalid CMUS command delimiter");
    }
    tokio::time::timeout(timeout, exchange(socket, command))
        .await
        .context("CMUS timed out")?
}

async fn exchange(socket: &Path, command: &str) -> Result<String> {
    let mut socket = UnixStream::connect(socket)
        .await
        .context("CMUS is not running")?;
    socket.write_all(format!("{command}\n").as_bytes()).await?;
    let mut response = Vec::new();
    let mut chunk = [0; 1024];
    loop {
        let count = socket.read(&mut chunk).await?;
        if count == 0 {
            bail!("CMUS closed the connection before replying");
        }
        response.extend_from_slice(&chunk[..count]);
        if response.len() > 65536 {
            bail!("CMUS response too large");
        }
        if response == b"\n" || response.ends_with(b"\n\n") {
            break;
        }
    }
    let response = String::from_utf8(response)?;
    if response.lines().any(|line| line.starts_with("error ")) {
        bail!("CMUS rejected the command");
    }
    Ok(response)
}

pub fn parse(text: &str) -> Result<Status> {
    let value = |prefix: &str| {
        text.lines()
            .find_map(|line| line.strip_prefix(prefix))
            .unwrap_or("")
    };
    let status = value("status ");
    if !matches!(status, "playing" | "paused" | "stopped") {
        bail!("Unexpected CMUS status");
    }
    let number = |prefix: &str| -> Result<u64> {
        let raw = value(prefix);
        if raw.is_empty() {
            Ok(0)
        } else {
            Ok(raw.parse()?)
        }
    };
    Ok(Status {
        effects: Default::default(),
        status: status.to_owned(),
        title: value("tag title ").to_owned(),
        artist: value("tag artist ").to_owned(),
        album: value("tag album ").to_owned(),
        position: number("position ")?,
        duration: number("duration ")?,
        repeat: if value("set repeat_current ") == "true" {
            "one"
        } else if value("set repeat ") == "true" {
            "all"
        } else {
            "off"
        }
        .to_owned(),
        shuffle: matches!(value("set shuffle "), "tracks" | "albums" | "true"),
        file: value("file ").to_owned(),
        track_id: None,
    })
}

pub fn neighbour(index: usize, len: usize, previous: bool, position: u64) -> Option<usize> {
    if previous && position > 3 {
        return Some(index);
    }
    if previous {
        index.checked_sub(1)
    } else {
        index.checked_add(1).filter(|next| *next < len)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_and_repeat_are_parsed_without_exposing_paths() {
        let status = parse("status paused\nfile /music/test.flac\nposition 12\nduration 90\nset repeat_current true\ntag title <script>\n\n").unwrap();
        assert_eq!(status.repeat, "one");
        assert_eq!(status.position, 12);
        assert!(!serde_json::to_string(&status).unwrap().contains("/music"));
        assert!(parse("error invalid\n").is_err());
        assert!(parse("status playing\nposition bad\n").is_err());
    }

    #[test]
    fn shuffle_modes_are_reported() {
        for (mode, expected) in [("off", false), ("tracks", true), ("albums", true)] {
            assert_eq!(
                parse(&format!("status stopped\nset shuffle {mode}\n"))
                    .unwrap()
                    .shuffle,
                expected
            );
        }
    }

    #[test]
    fn previous_restarts_after_three_seconds_and_edges_do_not_wrap() {
        assert_eq!(neighbour(0, 3, true, 0), None);
        assert_eq!(neighbour(0, 3, true, 4), Some(0));
        assert_eq!(neighbour(2, 3, false, 0), None);
        assert_eq!(neighbour(1, 3, true, 2), Some(0));
    }

    #[tokio::test]
    async fn unresponsive_socket_times_out() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("cmus");
        let listener = tokio::net::UnixListener::bind(&path).unwrap();
        let task = tokio::spawn(async move {
            let (_socket, _) = listener.accept().await.unwrap();
            std::future::pending::<()>().await;
        });
        let error = command(&path, "status", Duration::from_millis(30))
            .await
            .unwrap_err();
        assert!(error.to_string().contains("timed out"));
        task.abort();
        assert!(task.await.unwrap_err().is_cancelled());
    }

    #[tokio::test]
    async fn socket_protocol_and_command_delimiters() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("cmus");
        let listener = tokio::net::UnixListener::bind(&path).unwrap();
        let task = tokio::spawn(async move {
            let (mut socket, _) = listener.accept().await.unwrap();
            let mut buffer = [0; 64];
            let n = socket.read(&mut buffer).await.unwrap();
            assert_eq!(&buffer[..n], b"status\n");
            socket.write_all(b"status paused\n\n").await.unwrap();
        });
        assert_eq!(
            command(&path, "status", Duration::from_secs(1))
                .await
                .unwrap(),
            "status paused\n\n"
        );
        task.await.unwrap();
        assert!(
            command(&path, "status\nquit", Duration::from_secs(1))
                .await
                .is_err()
        );
    }
}
