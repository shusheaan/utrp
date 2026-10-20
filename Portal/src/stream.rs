//! Reuse the owner's pinned Rust API and existing auth file, never return cookies.
use crate::{config::StreamConfig, library::Track, mpv};
use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::{collections::HashMap, time::Duration};
use ytmusic_api::InnerTubeClient;
#[derive(Debug)]
pub struct Expired;
impl std::fmt::Display for Expired {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Stream list expired; Refresh")
    }
}
impl std::error::Error for Expired {}

#[derive(Default)]
pub struct StreamState {
    pub catalog: HashMap<String, Track>,
    pub queue: Vec<Track>,
}

#[derive(Clone, Serialize)]
pub struct Item {
    pub kind: &'static str,
    pub id: String,
    pub title: String,
    pub subtitle: String,
    pub section: String,
}

#[derive(Serialize)]
pub struct Page {
    pub account: String,
    pub items: Vec<Item>,
    pub next_cursor: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Browse {
    pub view: String,
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub query: String,
    #[serde(default)]
    pub cursor: String,
}

pub fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 160
        && id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}
pub fn valid_video(id: &str) -> bool {
    id.len() == 11 && valid_id(id)
}

pub(crate) fn track_item(
    track: ytmusic_api::Track,
    section: &str,
    tracks: &mut Vec<Track>,
) -> Option<Item> {
    if !valid_video(&track.video_id) || track.title.trim().is_empty() {
        return None;
    }
    let item = Item {
        kind: "track",
        id: track.video_id.clone(),
        title: track.title.clone(),
        subtitle: track.artist.clone(),
        section: section.to_owned(),
    };
    tracks.push(Track {
        id: track.video_id,
        title: track.title,
        artist: track.artist,
        album: track.album,
    });
    Some(item)
}
pub(crate) fn playlist_item(p: ytmusic_api::PlaylistInfo, section: &str) -> Item {
    Item {
        kind: if p.playlist_id.starts_with("MPRE") {
            "album"
        } else {
            "playlist"
        },
        id: p.playlist_id,
        title: p.title,
        subtitle: if p.track_count > 0 {
            format!("{} tracks", p.track_count)
        } else {
            "Playlist".into()
        },
        section: section.into(),
    }
}

pub async fn browse(config: &StreamConfig, request: &Browse) -> Result<(Page, Vec<Track>)> {
    ensure!(
        request.cursor.is_empty(),
        "Cursor not supported for this view"
    );
    ensure!(
        matches!(
            request.view.as_str(),
            "playlists" | "search" | "album" | "artist"
        ),
        "Unknown Stream view"
    );
    if matches!(request.view.as_str(), "album" | "artist") {
        ensure!(valid_id(&request.id), "Invalid catalog ID");
    }
    if request.view == "search" {
        ensure!(
            !request.query.trim().is_empty() && request.query.len() <= 300,
            "Enter a search query (up to 300 bytes)"
        );
    }
    // Reload for every browse, so `ytm -auth` takes effect without a Portal restart.
    let client = InnerTubeClient::from_auth_path(&config.auth_file)?;
    let account = client.get_account_info().await?.account_name;
    let mut tracks = Vec::new();
    let mut items = Vec::new();
    match request.view.as_str() {
        "album" => {
            let rows = client.get_album(&request.id).await?.tracks;
            items.extend(
                rows.into_iter()
                    .filter_map(|t| track_item(t, "", &mut tracks)),
            );
        }
        "playlists" => items.extend(
            client
                .get_library_playlists(config.list_limit)
                .await?
                .into_iter()
                .map(|p| playlist_item(p, "")),
        ),
        "search" => items.extend(crate::stream_catalog::search_items(
            crate::stream_catalog::search(&client, request.query.trim(), config.list_limit).await?,
            &mut tracks,
        )),
        "artist" => items.extend(crate::stream_catalog::artist_items(
            client.get_artist(&request.id).await?,
            &mut tracks,
        )),
        _ => unreachable!(),
    }
    Ok((
        Page {
            account,
            items,
            next_cursor: None,
        },
        tracks,
    ))
}

pub fn queue(
    state: &StreamState,
    ids: &[String],
    index: usize,
    metadata: &[Track],
) -> Result<Vec<Track>> {
    ensure!(
        !ids.is_empty() && ids.len() <= 500 && index < ids.len(),
        "Select between 1 and 500 tracks and a valid index"
    );
    ensure!(
        metadata.is_empty() || metadata.len() == ids.len(),
        "Invalid queue metadata count"
    );
    for (track, id) in metadata.iter().zip(ids) {
        ensure!(track.id == *id, "Queue metadata ID mismatch");
        ensure!(
            [&track.title, &track.artist, &track.album]
                .iter()
                .all(|s| s.len() <= 1024),
            "Queue metadata too long"
        );
    }
    ids.iter()
        .enumerate()
        .map(|(index, id)| {
            ensure!(valid_video(id), "Invalid video ID");
            // A valid video ID is a stable reference, not a capability issued by the catalog.
            // Old browser pages remain playable after eviction or a web-server restart.
            Ok(state
                .catalog
                .get(id)
                .or_else(|| state.queue.iter().find(|track| track.id == *id))
                .or_else(|| metadata.get(index))
                .cloned()
                .unwrap_or_else(|| Track {
                    id: id.clone(),
                    title: String::new(),
                    artist: String::new(),
                    album: String::new(),
                }))
        })
        .collect()
}

pub async fn load(
    config: &StreamConfig,
    tracks: &[Track],
    index: usize,
    shuffle: bool,
    timeout: Duration,
) -> Result<()> {
    mpv::commands(
        &config.mpv_socket,
        load_commands(tracks, index, shuffle),
        timeout,
    )
    .await?;
    Ok(())
}

fn load_commands(tracks: &[Track], index: usize, shuffle: bool) -> Vec<serde_json::Value> {
    let mut commands = vec![
        json!(["set_property", "pause", true]),
        json!(["stop"]),
        json!(["playlist-clear"]),
    ];
    // Append without starting. Choose the selected item only after the queue is complete.
    commands.extend(tracks.iter().map(|t| {
        json!([
            "loadfile",
            format!("https://music.youtube.com/watch?v={}", t.id),
            "append"
        ])
    }));
    // The player owns these labels for exactly as long as it owns the queue.
    // Replace the map rather than accumulating unrelated browse history.
    let metadata: HashMap<_, _> = tracks.iter().map(|t| (&t.id, t)).collect();
    commands.push(json!(["set_property", "user-data/portal-tracks", metadata]));
    commands.push(json!(["set_property", "playlist-pos", index]));
    if shuffle {
        commands.push(json!(["playlist-shuffle"]));
    }
    commands.push(json!(["set_property", "pause", false]));
    commands
}

#[derive(Serialize)]
pub struct Status {
    pub effects: crate::effects::View,
    pub status: &'static str,
    pub title: String,
    pub artist: String,
    pub album: String,
    pub track_id: Option<String>,
    pub position: u64,
    pub duration: u64,
    pub repeat: &'static str,
    pub shuffle: bool,
    pub error: Option<&'static str>,
}

pub async fn status(
    config: &StreamConfig,
    state: &StreamState,
    timeout: Duration,
) -> Result<Status> {
    let mut status = Status {
        effects: Default::default(),
        status: "stopped",
        title: String::new(),
        artist: String::new(),
        album: String::new(),
        track_id: None,
        position: 0,
        duration: 0,
        repeat: "one",
        shuffle: false,
        error: None,
    };
    if !mpv::available(&config.mpv_socket).await? {
        return Ok(status);
    }
    let properties = [
        "pause",
        "time-pos",
        "duration",
        "idle-active",
        "loop-file",
        "loop-playlist",
        "path",
        "core-idle",
        "eof-reached",
        "media-title",
        "shuffle",
    ];
    let p = mpv::commands(
        &config.mpv_socket,
        properties
            .iter()
            .map(|p| json!(["get_property", p]))
            .collect(),
        timeout,
    )
    .await?;
    status.status = if p[3] == true {
        "stopped"
    } else if p[0] == true {
        "paused"
    } else if p[7] == true {
        "loading"
    } else {
        "playing"
    };
    status.shuffle = p[10]
        .as_bool()
        .ok_or_else(|| anyhow::anyhow!("Invalid mpv shuffle state"))?;
    status.position = p[1].as_f64().unwrap_or(0.0).max(0.0) as u64;
    status.duration = p[2].as_f64().unwrap_or(0.0).max(0.0) as u64;
    status.repeat = if p[4] == "inf" {
        "one"
    } else if p[5] == "inf" {
        "all"
    } else {
        "off"
    };
    let id = p[6]
        .as_str()
        .and_then(|s| s.strip_prefix("https://music.youtube.com/watch?v="));
    status.track_id = id.filter(|id| valid_video(id)).map(str::to_owned);
    status.title = p[9].as_str().unwrap_or("").to_owned();
    if let Some(track) =
        current_metadata(config, state, status.track_id.as_deref(), timeout).await?
    {
        if !track.title.is_empty() {
            status.title = track.title.clone();
        }
        status.artist = track.artist.clone();
        status.album = track.album.clone();
        status.track_id = Some(track.id.clone());
    }
    if p[3] == true && !state.queue.is_empty() && p[8] != true {
        status.error = Some(
            "Stream stopped. Select the track again to retry with a fresh URL; check portal logs if it persists.",
        );
    }
    Ok(status)
}

async fn current_metadata(
    config: &StreamConfig,
    state: &StreamState,
    id: Option<&str>,
    timeout: Duration,
) -> Result<Option<Track>> {
    let Some(id) = id else {
        return Ok(None);
    };
    if let Some(track) = state.queue.iter().find(|t| t.id == id) {
        return Ok(Some(track.clone()));
    }
    // Read only one bounded entry, never the whole (potentially 500-song) map.
    let values = mpv::commands(
        &config.mpv_socket,
        vec![json!([
            "get_property",
            format!("user-data/portal-tracks/{id}")
        ])],
        timeout,
    )
    .await?;
    if values[0].is_null() {
        return Ok(None);
    }
    let track: Track = serde_json::from_value(values[0].clone())?;
    ensure!(track.id == id, "Player metadata ID mismatch");
    Ok(Some(track))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reject_urls_and_paths_but_accept_uncached_video_ids() {
        assert!(valid_video("dQw4w9WgXcQ"));
        for id in ["../secret", "https://evil", "abc\nquit", ""] {
            assert!(!valid_video(id));
        }
        assert!(queue(&StreamState::default(), &["dQw4w9WgXcQ".into()], 0, &[]).is_ok());
        assert!(queue(&StreamState::default(), &[], 0, &[]).is_err());
    }
    fn track() -> Track {
        Track {
            id: "dQw4w9WgXcQ".into(),
            title: "Test".into(),
            artist: "Artist".into(),
            album: String::new(),
        }
    }

    #[test]
    fn bounded_queue_requires_valid_selection() {
        let track = track();
        let state = StreamState {
            catalog: HashMap::from([(track.id.clone(), track.clone())]),
            queue: vec![],
        };
        assert_eq!(
            queue(&state, std::slice::from_ref(&track.id), 0, &[]).unwrap()[0].id,
            track.id
        );
        assert!(queue(&state, std::slice::from_ref(&track.id), 1, &[]).is_err());
        assert!(queue(&state, &vec![track.id.clone(); 501], 0, &[]).is_err());
    }

    #[test]
    fn new_queue_preserves_shuffle_before_unpausing() {
        let commands = load_commands(&[track()], 0, true);
        let count = commands.len();
        assert_eq!(
            commands[count - 3],
            json!(["set_property", "playlist-pos", 0])
        );
        assert_eq!(commands[count - 2], json!(["playlist-shuffle"]));
        assert_eq!(commands[count - 1], json!(["set_property", "pause", false]));
    }

    #[test]
    fn selection_unpauses_only_after_queue_is_ready() {
        let commands = load_commands(&[track()], 0, false);
        assert_eq!(commands[0], json!(["set_property", "pause", true]));
        assert_eq!(
            commands[3],
            json!([
                "loadfile",
                "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
                "append"
            ])
        );
        assert_eq!(
            commands[commands.len() - 2],
            json!(["set_property", "playlist-pos", 0])
        );
        assert_eq!(
            commands.last().unwrap(),
            &json!(["set_property", "pause", false])
        );
    }
}

#[cfg(test)]
#[path = "stream_reliability_tests.rs"]
mod reliability_tests;
