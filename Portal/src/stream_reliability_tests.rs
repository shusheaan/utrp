use super::*;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

fn track() -> Track {
    Track {
        id: "abcdefghijk".into(),
        title: "Song".into(),
        artist: "Artist".into(),
        album: "Album".into(),
    }
}
fn config(path: &std::path::Path) -> StreamConfig {
    StreamConfig {
        auth_file: path.join("unused"),
        mpv_socket: path.join("mpv.sock"),
        fetch_timeout_seconds: 10,
        list_limit: 100,
    }
}

#[test]
fn browser_snapshot_survives_cache_eviction_and_rejects_untrusted_metadata() {
    let t = track();
    let ids = vec![t.id.clone()];
    let metadata = vec![t.clone()];
    let restored = queue(&StreamState::default(), &ids, 0, &metadata).unwrap();
    assert_eq!(restored[0].artist, "Artist");
    // An older browser without metadata can still play a stable ID.
    assert_eq!(
        queue(&StreamState::default(), &ids, 0, &[]).unwrap()[0].id,
        t.id
    );
    for id in ["https://bad", "../private", "abcdefghij\n"] {
        assert!(queue(&StreamState::default(), &[id.into()], 0, &[]).is_err());
    }
    assert!(queue(&StreamState::default(), &ids, 0, &[t.clone(), t.clone()]).is_err());
    let mut invalid = t.clone();
    invalid.id = "12345678901".into();
    assert!(queue(&StreamState::default(), &ids, 0, &[invalid]).is_err());
    let mut invalid = t.clone();
    invalid.artist = "x".repeat(1025);
    assert!(queue(&StreamState::default(), &ids, 0, &[invalid]).is_err());
    let state = StreamState {
        catalog: HashMap::new(),
        queue: vec![t],
    };
    assert_eq!(queue(&state, &ids, 0, &[]).unwrap()[0].album, "Album");
    let commands = load_commands(&metadata, 0, false);
    let saved = commands
        .iter()
        .find(|c| c[1] == "user-data/portal-tracks")
        .unwrap();
    assert_eq!(saved[2][&ids[0]]["artist"], "Artist");
}

#[tokio::test]
async fn fresh_web_state_restores_player_metadata_and_missing_fields_are_safe() {
    for saved in [Some(track()), None] {
        let has_metadata = saved.is_some();
        let dir = tempfile::tempdir().unwrap();
        let config = config(dir.path());
        let listener = tokio::net::UnixListener::bind(&config.mpv_socket).unwrap();
        let worker = tokio::spawn(async move {
            // status first checks availability, then reads properties, then metadata.
            for _ in 0..3 {
                let (socket, _) = listener.accept().await.unwrap();
                let mut reader = BufReader::new(socket);
                loop {
                    let mut line = String::new();
                    if reader.read_line(&mut line).await.unwrap() == 0 {
                        break;
                    }
                    let request: serde_json::Value = serde_json::from_str(&line).unwrap();
                    let property = request["command"][1].as_str().unwrap();
                    let data = match property {
                        "path" => json!("https://music.youtube.com/watch?v=abcdefghijk"),
                        "pause" | "idle-active" | "core-idle" | "eof-reached" | "shuffle" => {
                            json!(false)
                        }
                        "duration" => json!(180),
                        "time-pos" => json!(50),
                        "media-title" => json!("Player title"),
                        "loop-file" => json!("inf"),
                        "loop-playlist" => json!("no"),
                        "user-data/portal-tracks/abcdefghijk" => json!(saved),
                        _ => panic!("Unexpected property {property}"),
                    };
                    let error = if data.is_null() {
                        "property not found"
                    } else {
                        "success"
                    };
                    let reply =
                        json!({"request_id":request["request_id"], "error":error, "data":data});
                    reader
                        .get_mut()
                        .write_all(format!("{reply}\n").as_bytes())
                        .await
                        .unwrap();
                }
            }
        });
        let status = status(&config, &StreamState::default(), Duration::from_secs(2))
            .await
            .unwrap();
        assert_eq!(status.status, "playing");
        assert_eq!(status.track_id.as_deref(), Some("abcdefghijk"));
        assert_eq!(status.artist, if has_metadata { "Artist" } else { "" });
        assert_eq!(
            status.title,
            if has_metadata { "Song" } else { "Player title" }
        );
        worker.await.unwrap();
    }
}

#[tokio::test]
#[ignore = "requires installed mpv; isolated idle null-audio player, no network"]
async fn real_mpv_null_audio_metadata_survives_web_state_reset() {
    let dir = tempfile::tempdir().unwrap();
    let config = config(dir.path());
    let mut player = tokio::process::Command::new("mpv")
        .args([
            "--no-config",
            "--idle=yes",
            "--ao=null",
            "--vo=null",
            "--no-terminal",
        ])
        .arg(format!(
            "--input-ipc-server={}",
            config.mpv_socket.display()
        ))
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .kill_on_drop(true)
        .spawn()
        .unwrap();
    for _ in 0..100 {
        if config.mpv_socket.exists() {
            break;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    let timeout = Duration::from_secs(2);
    let t = track();
    assert!(
        current_metadata(&config, &StreamState::default(), Some(&t.id), timeout)
            .await
            .unwrap()
            .is_none()
    );
    mpv::commands(
        &config.mpv_socket,
        vec![json!(["set_property", "user-data/portal-tracks", {t.id.clone(): t}])],
        timeout,
    )
    .await
    .unwrap();
    for _ in 0..3 {
        let restored = current_metadata(&config, &StreamState::default(), Some(&t.id), timeout)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(restored.artist, "Artist");
    }
    assert!(
        current_metadata(
            &config,
            &StreamState::default(),
            Some("12345678901"),
            timeout
        )
        .await
        .unwrap()
        .is_none()
    );
    // Only our optional map entries tolerate missing-property errors.
    assert!(
        mpv::commands(
            &config.mpv_socket,
            vec![json!(["get_property", "no-such-property"])],
            timeout
        )
        .await
        .is_err()
    );
    player.kill().await.unwrap();
    player.wait().await.unwrap();
}
