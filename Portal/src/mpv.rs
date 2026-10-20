//! Private Unix JSON IPC. Never expose arbitrary commands through HTTP.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{path::Path, time::Duration};
use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader},
    net::UnixStream,
};

pub async fn commands(path: &Path, commands: Vec<Value>, timeout: Duration) -> Result<Vec<Value>> {
    tokio::time::timeout(timeout, exchange(path, commands))
        .await
        .context("mpv timed out")?
}

async fn exchange(path: &Path, commands: Vec<Value>) -> Result<Vec<Value>> {
    let stream = UnixStream::connect(path)
        .await
        .context("Stream player unavailable")?;
    let (reader, mut writer) = stream.into_split();
    let mut reader = BufReader::new(reader);
    let mut results = Vec::new();
    for (id, command) in commands.into_iter().enumerate() {
        writer
            .write_all(format!("{}\n", json!({"command":command,"request_id":id})).as_bytes())
            .await?;
        loop {
            let mut line = String::new();
            let n = (&mut reader).take(65537).read_line(&mut line).await?;
            ensure!(n > 0 && n <= 65536, "Invalid mpv response length");
            let response: Value = serde_json::from_str(&line)?;
            if response["request_id"].as_u64() != Some(id as u64) {
                continue;
            }
            // A property can be unavailable while a track is loading or stopped.
            if response["error"] == "property unavailable" && command[0] == "get_property" {
                results.push(Value::Null);
            } else {
                ensure!(response["error"] == "success", "mpv rejected a command");
                results.push(response["data"].clone());
            }
            break;
        }
    }
    Ok(results)
}

pub async fn available(path: &Path) -> Result<bool> {
    match UnixStream::connect(path).await {
        Ok(_) => Ok(true),
        Err(e)
            if matches!(
                e.kind(),
                std::io::ErrorKind::NotFound | std::io::ErrorKind::ConnectionRefused
            ) =>
        {
            Ok(false)
        }
        Err(e) => Err(e.into()),
    }
}

pub async fn pause_if_running(path: &Path, timeout: Duration) -> Result<()> {
    if available(path).await? {
        commands(path, vec![json!(["set_property", "pause", true])], timeout).await?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[tokio::test]
    async fn matches_responses_and_skips_events() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("mpv");
        let listener = tokio::net::UnixListener::bind(&path).unwrap();
        let worker = tokio::spawn(async move {
            let (socket, _) = listener.accept().await.unwrap();
            let mut reader = BufReader::new(socket);
            let mut line = String::new();
            reader.read_line(&mut line).await.unwrap();
            assert_eq!(
                serde_json::from_str::<Value>(&line).unwrap()["command"],
                json!(["get_property", "pause"])
            );
            reader.get_mut().write_all(b"{\"event\":\"idle\"}\n{\"request_id\":0,\"error\":\"success\",\"data\":true}\n").await.unwrap();
        });
        assert_eq!(
            commands(
                &path,
                vec![json!(["get_property", "pause"])],
                Duration::from_secs(1)
            )
            .await
            .unwrap(),
            vec![json!(true)]
        );
        worker.await.unwrap();
    }
}
