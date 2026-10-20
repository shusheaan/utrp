//! Preserve the account's real Home shelf names and ordering.
use crate::{
    library::Track,
    stream::{Item, valid_id, valid_video},
};
use anyhow::{Result, ensure};
use serde_json::Value;

const INITIAL: &str =
    "/contents/singleColumnBrowseResultsRenderer/tabs/0/tabRenderer/content/sectionListRenderer";
const CONTINUED: &str = "/continuationContents/sectionListContinuation";
const KIND: &str = "/browseEndpoint/browseEndpointContextSupportedConfigs/browseEndpointContextMusicConfig/pageType";

pub struct Batch {
    pub items: Vec<Item>,
    pub tracks: Vec<Track>,
    pub next: Option<String>,
}
fn string<'a>(value: &'a Value, path: &str) -> Option<&'a str> {
    value.pointer(path).and_then(Value::as_str)
}
fn label(value: &Value, path: &str) -> String {
    value
        .pointer(path)
        .and_then(Value::as_array)
        .map(|runs| runs.iter().filter_map(|r| string(r, "/text")).collect())
        .unwrap_or_default()
}
fn artist(data: &Value) -> String {
    let Some(runs) = data.pointer("/subtitle/runs").and_then(Value::as_array) else {
        return String::new();
    };
    runs.iter()
        .filter(|r| {
            r.pointer("/navigationEndpoint/browseEndpoint/browseId")
                .and_then(Value::as_str)
                .is_some_and(|id| id.starts_with("UC"))
        })
        .filter_map(|r| string(r, "/text"))
        .collect::<Vec<_>>()
        .join(", ")
}
fn from_track(track: Track, section: &str, tracks: &mut Vec<Track>) -> Item {
    let item = Item {
        kind: "track",
        id: track.id.clone(),
        title: track.title.clone(),
        subtitle: track.artist.clone(),
        section: section.into(),
    };
    tracks.push(track);
    item
}
fn card(data: &Value, section: &str, tracks: &mut Vec<Track>) -> Option<Item> {
    let title = label(data, "/title/runs");
    if title.is_empty() {
        return None;
    }
    let endpoint = data
        .pointer("/title/runs/0/navigationEndpoint")
        .or_else(|| data.get("navigationEndpoint"))?;
    let kind = string(endpoint, KIND).unwrap_or("");
    let author = artist(data);
    if let Some(id) = string(endpoint, "/watchEndpoint/videoId").filter(|id| valid_video(id)) {
        return Some(from_track(
            Track {
                id: id.into(),
                title,
                artist: author,
                album: String::new(),
            },
            section,
            tracks,
        ));
    }
    let (item_kind, id) = match kind {
        "MUSIC_PAGE_TYPE_ARTIST" | "MUSIC_PAGE_TYPE_USER_CHANNEL" => {
            ("artist", string(endpoint, "/browseEndpoint/browseId")?)
        }
        "MUSIC_PAGE_TYPE_ALBUM" => ("album", string(endpoint, "/browseEndpoint/browseId")?),
        "MUSIC_PAGE_TYPE_PLAYLIST" => (
            "playlist",
            string(endpoint, "/browseEndpoint/browseId")?.trim_start_matches("VL"),
        ),
        _ => (
            "playlist",
            string(endpoint, "/watchPlaylistEndpoint/playlistId")
                .or_else(|| string(endpoint, "/watchEndpoint/playlistId"))?,
        ),
    };
    if !valid_id(id) {
        return None;
    }
    Some(Item {
        kind: item_kind,
        id: id.into(),
        title,
        subtitle: if author.is_empty() {
            match item_kind {
                "artist" => "Artist",
                "album" => "Album",
                _ => "Playlist",
            }
            .into()
        } else {
            author
        },
        section: section.into(),
    })
}
pub fn parse(response: &Value) -> Result<Batch> {
    let shelf = response
        .pointer(INITIAL)
        .or_else(|| response.pointer(CONTINUED))
        .ok_or_else(|| anyhow::anyhow!("Unknown Home envelope"))?;
    let rows = shelf
        .get("contents")
        .and_then(Value::as_array)
        .ok_or_else(|| anyhow::anyhow!("Missing Home shelves"))?;
    let next = string(shelf, "/continuations/0/nextContinuationData/continuation").or_else(|| {
        rows.last().and_then(|r| {
            string(
                r,
                "/continuationItemRenderer/continuationEndpoint/continuationCommand/token",
            )
        })
    });
    ensure!(
        next.is_none_or(|t| !t.is_empty() && t.len() <= 16384),
        "Invalid Home token"
    );
    let mut batch = Batch {
        items: Vec::new(),
        tracks: Vec::new(),
        next: next.map(str::to_owned),
    };
    for row in rows {
        let Some(data) = row.get("musicCarouselShelfRenderer") else {
            continue;
        };
        let section = label(
            data,
            "/header/musicCarouselShelfBasicHeaderRenderer/title/runs",
        );
        let Some(contents) = data.get("contents").and_then(Value::as_array) else {
            continue;
        };
        for entry in contents {
            let item = if let Some(data) = entry.get("musicTwoRowItemRenderer") {
                card(data, &section, &mut batch.tracks)
            } else {
                crate::liked_parse::track(entry).map(|t| from_track(t, &section, &mut batch.tracks))
            };
            if let Some(item) = item {
                batch.items.push(item)
            }
        }
    }
    Ok(batch)
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn continues_real_sections_and_routes_home_cards() {
        let mut cards = Vec::new();
        for (kind, id) in [
            ("ARTIST", "UCone"),
            ("ALBUM", "MPREone"),
            ("PLAYLIST", "VLPLone"),
        ] {
            cards.push(json!({"musicTwoRowItemRenderer":{"title":{"runs":[{"text":kind,"navigationEndpoint":{"browseEndpoint":{"browseId":id,"browseEndpointContextSupportedConfigs":{"browseEndpointContextMusicConfig":{"pageType":format!("MUSIC_PAGE_TYPE_{kind}")}}}}}]}}}));
        }
        let raw = json!({"continuationContents":{"sectionListContinuation":{"contents":[{"musicCarouselShelfRenderer":{"header":{"musicCarouselShelfBasicHeaderRenderer":{"title":{"runs":[{"text":"For you"}]}}},"contents":cards}}],"continuations":[{"nextContinuationData":{"continuation":"private"}}]}}});
        let parsed = parse(&raw).unwrap();
        assert_eq!(parsed.items.len(), 3);
        assert!(parsed.items.iter().all(|i| i.section == "For you"));
        assert_eq!(parsed.items[0].kind, "artist");
        assert_eq!(parsed.items[1].kind, "album");
        assert_eq!(parsed.items[2].id, "PLone");
        assert_eq!(parsed.next.as_deref(), Some("private"));
        assert!(parse(&json!({})).is_err());
    }
}
