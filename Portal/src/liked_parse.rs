//! Small read-only adapter for the playlist shelves used by the pinned Rust API.
//! Only Portal's title/artist/album/video ID fields are retained.
use crate::{library::Track, stream::valid_video};
use anyhow::{Result, ensure};
use serde_json::Value;

const INITIAL: &str = "/contents/twoColumnBrowseResultsRenderer/secondaryContents/sectionListRenderer/contents/0/musicPlaylistShelfRenderer";
const MODERN: &str = "/onResponseReceivedActions/0/appendContinuationItemsAction/continuationItems";
const LEGACY: &str = "/continuationContents/musicPlaylistShelfContinuation";
const TOKEN: &str = "/continuationItemRenderer/continuationEndpoint/continuationCommand/token";
const LEGACY_TOKEN: &str = "/continuations/0/nextContinuationData/continuation";
const PLAY_ID: &str = "/overlay/musicItemThumbnailOverlayRenderer/content/musicPlayButtonRenderer/playNavigationEndpoint/watchEndpoint/videoId";
const PAGE_TYPE: &str = "/navigationEndpoint/browseEndpoint/browseEndpointContextSupportedConfigs/browseEndpointContextMusicConfig/pageType";

pub fn parse(response: &Value) -> Result<(Vec<Track>, Option<String>)> {
    let shelf = response
        .pointer(INITIAL)
        .or_else(|| response.pointer(LEGACY));
    let rows = response
        .pointer(MODERN)
        .or_else(|| shelf.and_then(|v| v.get("contents")))
        .and_then(Value::as_array)
        .ok_or_else(|| anyhow::anyhow!("Unrecognized playlist response"))?;
    let next = rows
        .last()
        .and_then(|v| v.pointer(TOKEN))
        .and_then(Value::as_str)
        .or_else(|| {
            shelf
                .and_then(|v| v.pointer(LEGACY_TOKEN))
                .and_then(Value::as_str)
        });
    ensure!(
        next.is_none_or(|t| !t.is_empty() && t.len() <= 16384),
        "Invalid upstream token"
    );
    Ok((
        rows.iter().filter_map(track).collect(),
        next.map(str::to_owned),
    ))
}

fn text(run: &Value) -> &str {
    run.get("text").and_then(Value::as_str).unwrap_or("")
}

pub(crate) fn track(row: &Value) -> Option<Track> {
    let data = row.get("musicResponsiveListItemRenderer")?;
    let id = data.pointer(PLAY_ID).or_else(|| data.pointer("/flexColumns/0/musicResponsiveListItemFlexColumnRenderer/text/runs/0/navigationEndpoint/watchEndpoint/videoId"))?.as_str()?;
    if !valid_video(id) {
        return None;
    }
    let columns = data.get("flexColumns")?.as_array()?;
    let (mut title, mut album, mut artist) = (None, String::new(), None);
    let mut fallback_artist = None;
    let mut channel_artist = None;
    for column in columns {
        let Some(runs) = column
            .pointer("/musicResponsiveListItemFlexColumnRenderer/text/runs")
            .and_then(Value::as_array)
        else {
            continue;
        };
        let Some(first) = runs.first() else { continue };
        let page_type = first
            .pointer(PAGE_TYPE)
            .and_then(Value::as_str)
            .unwrap_or("");
        let names = || {
            runs.iter()
                .step_by(2)
                .map(text)
                .collect::<Vec<_>>()
                .join(", ")
        };
        if first.pointer("/navigationEndpoint/watchEndpoint").is_some()
            || page_type == "MUSIC_PAGE_TYPE_NON_MUSIC_AUDIO_TRACK_PAGE"
        {
            title = Some(text(first).to_owned());
        } else {
            match page_type {
                "MUSIC_PAGE_TYPE_ARTIST" | "MUSIC_PAGE_TYPE_UNKNOWN" => artist = Some(names()),
                "MUSIC_PAGE_TYPE_ALBUM" | "MUSIC_PAGE_TYPE_AUDIOBOOK" => {
                    album = text(first).to_owned()
                }
                "MUSIC_PAGE_TYPE_USER_CHANNEL" => channel_artist = Some(names()),
                _ if first.get("navigationEndpoint").is_none() && fallback_artist.is_none() => {
                    let value = text(first);
                    if !value.contains(':')
                        || !value.chars().all(|c| c.is_ascii_digit() || c == ':')
                    {
                        fallback_artist = Some(names());
                    }
                }
                _ => {}
            }
        }
    }
    let title = title?;
    if title.is_empty() || title == "Song deleted" {
        return None;
    }
    Some(Track {
        id: id.into(),
        title,
        album,
        artist: artist
            .or(fallback_artist)
            .or(channel_artist)
            .unwrap_or_else(|| "Unknown Artist".into()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn modern_and_legacy_pages_and_unknown_shape() {
        let token = json!({"continuationItemRenderer":{"continuationEndpoint":{"continuationCommand":{"token":"next"}}}});
        let modern = json!({"onResponseReceivedActions":[{"appendContinuationItemsAction":{"continuationItems":[token]}}]});
        assert_eq!(parse(&modern).unwrap().1.as_deref(), Some("next"));
        let legacy = json!({"continuationContents":{"musicPlaylistShelfContinuation":{"contents":[],"continuations":[{"nextContinuationData":{"continuation":"legacy"}}]}}});
        assert_eq!(parse(&legacy).unwrap().1.as_deref(), Some("legacy"));
        assert!(parse(&json!({"error":"wrong shape"})).is_err());
        let empty = json!({"onResponseReceivedActions":[{"appendContinuationItemsAction":{"continuationItems":[]}}]});
        assert!(parse(&empty).unwrap().1.is_none());
    }
    #[test]
    fn resolves_columns_and_skips_unavailable_songs() {
        let col = |runs: Value| json!({"musicResponsiveListItemFlexColumnRenderer":{"text":{"runs":runs}}});
        let browse = |name: &str, kind: &str| json!({"text":name,"navigationEndpoint":{"browseEndpoint":{"browseEndpointContextSupportedConfigs":{"browseEndpointContextMusicConfig":{"pageType":kind}}}}});
        let row = json!({"musicResponsiveListItemRenderer":{
            "overlay":{"musicItemThumbnailOverlayRenderer":{"content":{"musicPlayButtonRenderer":{"playNavigationEndpoint":{"watchEndpoint":{"videoId":"abcdefghijk"}}}}}},
            "flexColumns":[col(json!([browse("Album", "MUSIC_PAGE_TYPE_ALBUM")])),
                col(json!([{"text":"Song","navigationEndpoint":{"watchEndpoint":{}}}])),
                col(json!([browse("A", "MUSIC_PAGE_TYPE_ARTIST"),{"text":" • "},browse("B", "MUSIC_PAGE_TYPE_ARTIST")]))]}});
        let parsed = track(&row).unwrap();
        assert_eq!(parsed.title, "Song");
        assert_eq!(parsed.album, "Album");
        assert_eq!(parsed.artist, "A, B");
        assert!(track(&json!({"musicResponsiveListItemRenderer":{"flexColumns":[]}})).is_none());
    }
}
