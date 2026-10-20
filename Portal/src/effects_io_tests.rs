//! Isolated IPC checks; the real mpv check uses a temporary silent file and --ao=null.
use super::*;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};

fn config(root: &std::path::Path) -> Config {
    serde_json::from_value(json!({"listen":"127.0.0.1:8787","music_root":root,
        "cmus_socket":root.join("cmus"),"public_origin":"https://example.test","allowed_login":"test",
        "request_timeout_seconds":1,"fade_seconds":0.15,
        "stream":{"auth_file":root.join("no-auth"),"mpv_socket":root.join("mpv"),"fetch_timeout_seconds":5,"list_limit":100}})).unwrap()
}

#[tokio::test]
async fn local_volume_is_software_only_and_seek_is_absolute() {
    let temp = tempfile::tempdir().unwrap();
    let config = config(temp.path());
    let listener = tokio::net::UnixListener::bind(&config.cmus_socket).unwrap();
    let server = tokio::spawn(async move {
        for expected in ["set softvol=true\n", "vol 37%\n", "seek 12\n"] {
            let (socket, _) = listener.accept().await.unwrap();
            let mut reader = BufReader::new(socket);
            let mut line = String::new();
            reader.read_line(&mut line).await.unwrap();
            assert_eq!(line, expected);
            reader.get_mut().write_all(b"\n").await.unwrap();
        }
    });
    volume(&config, Source::Local, 37).await.unwrap();
    seek(&config, Source::Local, 12.0).await.unwrap();
    server.await.unwrap();
}

#[tokio::test]
async fn missing_players_do_not_start_any_services_on_recovery() {
    let temp = tempfile::tempdir().unwrap();
    restore(&config(temp.path())).await.unwrap();
}

#[test]
fn missing_fade_setting_defaults_to_short_fade() {
    let mut value = serde_json::to_value(config(std::path::Path::new("/tmp/test"))).unwrap();
    value.as_object_mut().unwrap().remove("fade_seconds");
    let config: Config = serde_json::from_value(value).unwrap();
    assert_eq!(config.fade_seconds, 0.75);
}

#[test]
fn effects_reject_arbitrary_commands_sources_and_invalid_fade_settings() {
    for body in [
        json!({"source":"system","action":"fade"}),
        json!({"source":"local","action":"quit"}),
        json!({"source":"local","action":"ab","command":"vol 0"}),
    ] {
        assert!(serde_json::from_value::<Request>(body).is_err());
    }
    let mut c = config(std::path::Path::new("/tmp/test"));
    for seconds in [0.0, 6.0, f64::NAN, f64::INFINITY] {
        c.fade_seconds = seconds;
        assert!(c.validate().is_err());
    }
}

fn silent_wave(path: &std::path::Path) {
    let bytes = 6_u32 * 8000 * 2;
    let mut data = Vec::new();
    data.extend(b"RIFF");
    data.extend((36 + bytes).to_le_bytes());
    data.extend(b"WAVEfmt ");
    data.extend(16_u32.to_le_bytes());
    data.extend(1_u16.to_le_bytes());
    data.extend(1_u16.to_le_bytes());
    data.extend(8000_u32.to_le_bytes());
    data.extend(16000_u32.to_le_bytes());
    data.extend(2_u16.to_le_bytes());
    data.extend(16_u16.to_le_bytes());
    data.extend(b"data");
    data.extend(bytes.to_le_bytes());
    data.resize(44 + bytes as usize, 0);
    std::fs::write(path, data).unwrap();
}

#[tokio::test]
#[ignore = "requires installed mpv; isolated null-audio playback, no network"]
async fn real_mpv_null_audio_loops_and_restores_volume() {
    let temp = tempfile::tempdir().unwrap();
    let c = config(temp.path());
    let socket = &c.stream.as_ref().unwrap().mpv_socket;
    let wav = temp.path().join("silence.wav");
    silent_wave(&wav);
    let mut process = tokio::process::Command::new("mpv")
        .args([
            "--no-config",
            "--ao=null",
            "--no-video",
            "--idle=yes",
            "--loop-file=inf",
            "--no-terminal",
        ])
        .arg(format!("--input-ipc-server={}", socket.display()))
        .arg(&wav)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .kill_on_drop(true)
        .spawn()
        .unwrap();
    for _ in 0..100 {
        if socket.exists() {
            break;
        }
        tokio::time::sleep(Duration::from_millis(20)).await;
    }
    let mut p = Player::default();
    let mut loops = 0;
    let mut gains = Vec::new();
    let start = Instant::now();
    let mut previous = Instant::now();
    while start.elapsed() < Duration::from_secs(5) {
        let values = mpv::commands(
            socket,
            vec![
                json!(["get_property", "time-pos"]),
                json!(["get_property", "duration"]),
            ],
            c.timeout(),
        )
        .await
        .unwrap();
        if let (Some(position), Some(duration)) = (values[0].as_f64(), values[1].as_f64()) {
            let snap = Snapshot {
                track: Some("fixture".into()),
                position,
                duration,
                playing: true,
                coarse: false,
            };
            if p.track.is_none() {
                p.observe(&snap);
                p.mark(1.0).unwrap();
                p.mark(2.5).unwrap();
                volume(&c, Source::Stream, 0).await.unwrap();
                p.volume = 0;
                seek(&c, Source::Stream, 1.0).await.unwrap();
            } else {
                let dt = previous.elapsed().as_secs_f64();
                let (gain, jump) = p.tick(&snap, dt, 0.3);
                set_gain(&c, Source::Stream, &mut p, gain).await.unwrap();
                gains.push(gain);
                if let Some(target) = jump {
                    seek(&c, Source::Stream, target).await.unwrap();
                    loops += 1;
                }
            }
        }
        previous = Instant::now();
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    assert!(loops >= 2, "AB did not repeat: {loops}");
    assert!(gains.iter().any(|g| *g < 20));
    assert!(gains.iter().any(|g| *g > 90));
    restore(&c).await.unwrap();
    assert_eq!(
        mpv::commands(socket, vec![json!(["get_property", "volume"])], c.timeout())
            .await
            .unwrap()[0]
            .as_f64(),
        Some(100.0)
    );
    process.kill().await.unwrap();
    process.wait().await.unwrap();
}

#[derive(Default)]
struct LocalFixture {
    position: f64,
    playing: bool,
    clock: Option<Instant>,
    seeks: usize,
    gains: Vec<u8>,
}

async fn local_fixture(
    listener: tokio::net::UnixListener,
    state: Arc<tokio::sync::Mutex<LocalFixture>>,
    file: String,
) {
    loop {
        let (socket, _) = listener.accept().await.unwrap();
        let mut reader = BufReader::new(socket);
        let mut line = String::new();
        reader.read_line(&mut line).await.unwrap();
        if line.is_empty() {
            continue;
        }
        let mut player = state.lock().await;
        let position = player.position
            + if player.playing {
                player
                    .clock
                    .map(|t| t.elapsed().as_secs_f64())
                    .unwrap_or(0.0)
            } else {
                0.0
            };
        let reply = if line == "status\n" {
            format!(
                "status {}\nfile {file}\nposition {}\nduration 20\n\n",
                if player.playing { "playing" } else { "paused" },
                position as u64
            )
        } else if let Some(value) = line.strip_prefix("seek ") {
            player.position = value.trim().parse().unwrap();
            player.clock = Some(Instant::now());
            player.seeks += 1;
            "\n".into()
        } else if let Some(value) = line.strip_prefix("vol ") {
            player
                .gains
                .push(value.trim().trim_end_matches('%').parse().unwrap());
            "\n".into()
        } else {
            assert_eq!(line, "set softvol=true\n");
            "\n".into()
        };
        drop(player);
        reader.get_mut().write_all(reply.as_bytes()).await.unwrap();
    }
}

#[tokio::test]
async fn local_ab_worker_runs_without_browser_and_restores_on_exit() {
    let temp = tempfile::tempdir().unwrap();
    let c = config(temp.path());
    let listener = tokio::net::UnixListener::bind(&c.cmus_socket).unwrap();
    let fixture = Arc::new(tokio::sync::Mutex::new(LocalFixture {
        position: 1.0,
        ..Default::default()
    }));
    let fixture_worker = tokio::spawn(local_fixture(
        listener,
        Arc::clone(&fixture),
        temp.path().join("test.wav").display().to_string(),
    ));
    let app = Arc::new(App {
        effects: tokio::sync::Mutex::new(Default::default()),
        stream: tokio::sync::Mutex::new(Default::default()),
        stream_fetch: tokio::sync::Semaphore::new(1),
        rating_requests: tokio::sync::Semaphore::new(1),
        liked: tokio::sync::Mutex::new(Default::default()),
        home: tokio::sync::Mutex::new(Default::default()),
        config: c,
        tracks: vec![],
        controls: tokio::sync::Mutex::new(()),
    });
    let request = || {
        Json(Request {
            source: Source::Local,
            action: Action::Ab,
            track_id: Some("test.wav".into()),
        })
    };
    let a = control(State(Arc::clone(&app)), request())
        .await
        .unwrap_or_else(|_| panic!("A failed"))
        .0;
    assert_eq!(a.a, Some(1.0));
    assert!(!a.fade);
    fixture.lock().await.position = 2.0;
    let b = control(State(Arc::clone(&app)), request())
        .await
        .unwrap_or_else(|_| panic!("B failed"))
        .0;
    assert!(b.forced && b.fade);
    assert_eq!(b.b, Some(2.0));
    let (stop_tx, stop_rx) = tokio::sync::watch::channel(false);
    {
        let mut f = fixture.lock().await;
        f.playing = true;
        f.clock = Some(Instant::now());
    }
    let worker = tokio::spawn(run(Arc::clone(&app), stop_rx));
    // No HTTP requests, no browser timer: the computer continues looping.
    tokio::time::sleep(Duration::from_millis(3300)).await;
    stop_tx.send(true).unwrap();
    worker.await.unwrap();
    let f = fixture.lock().await;
    assert!(f.seeks >= 3, "background loop did not run: {}", f.seeks);
    assert!(f.gains.contains(&0));
    assert!(f.gains.iter().any(|g| *g > 90));
    assert_eq!(f.gains.last(), Some(&100));
    drop(f);
    fixture_worker.abort();
}
