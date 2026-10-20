//! Incremental playlist browsing (including both Liked entry points). Upstream tokens never leave the server.
use crate::{
    config::StreamConfig,
    library::Track,
    stream::{Browse, Expired, Item, Page},
};
use anyhow::{Result, ensure};
use serde_json::json;
use std::{
    collections::HashSet,
    hash::{DefaultHasher, Hash, Hasher},
    time::{SystemTime, UNIX_EPOCH},
};
use ytmusic_api::InnerTubeClient;

pub const PAGE_SIZE: usize = 100;

#[derive(Clone)]
struct Session {
    generation: u128,
    auth_hash: u64,
    browse_id: String,
    account: String,
    tracks: Vec<Track>,
    next: Option<String>,
    tokens: HashSet<String>,
}

#[derive(Default)]
pub struct Cache {
    session: Option<Session>,
}

fn fingerprint(bytes: &[u8]) -> u64 {
    let mut hash = DefaultHasher::new();
    bytes.hash(&mut hash);
    hash.finish()
}

fn offset(cursor: &str, session: &Session) -> Result<usize> {
    ensure!(cursor.len() <= 64, "Invalid playlist cursor");
    let (generation, offset) = cursor
        .split_once(':')
        .ok_or_else(|| anyhow::anyhow!("Invalid playlist cursor"))?;
    ensure!(generation.parse::<u128>()? == session.generation, Expired);
    let offset = offset.parse::<usize>()?;
    ensure!(
        offset > 0 && offset.is_multiple_of(PAGE_SIZE) && offset <= session.tracks.len(),
        "Invalid playlist offset"
    );
    Ok(offset)
}

fn page(session: &Session, start: usize) -> (Page, Vec<Track>) {
    let end = (start + PAGE_SIZE).min(session.tracks.len());
    let tracks = session.tracks[start..end].to_vec();
    let items = tracks
        .iter()
        .map(|t| Item {
            kind: "track",
            id: t.id.clone(),
            title: t.title.clone(),
            subtitle: t.artist.clone(),
            section: String::new(),
        })
        .collect();
    let next_cursor = (end < session.tracks.len() || session.next.is_some())
        .then(|| format!("{}:{end}", session.generation));
    (
        Page {
            account: session.account.clone(),
            items,
            next_cursor,
        },
        tracks,
    )
}

fn append(session: &mut Session, response: &serde_json::Value) -> Result<()> {
    let (tracks, next) = crate::liked_parse::parse(response)?;
    if let Some(token) = &next {
        ensure!(
            session.tokens.insert(token.clone()),
            "Repeated upstream continuation"
        );
    }
    let mut ids: HashSet<String> = session.tracks.iter().map(|t| t.id.clone()).collect();
    session
        .tracks
        .extend(tracks.into_iter().filter(|t| ids.insert(t.id.clone())));
    ensure!(
        session.tracks.len() <= 10000,
        "Playlist cache limit exceeded"
    );
    session.next = next;
    Ok(())
}

fn browse_id(request: &Browse) -> Result<String> {
    match request.view.as_str() {
        "liked" => Ok("VLLM".into()),
        "playlist" => {
            ensure!(crate::stream::valid_id(&request.id), "Invalid playlist ID");
            Ok(if request.id.starts_with("VL") {
                request.id.clone()
            } else {
                format!("VL{}", request.id)
            })
        }
        _ => anyhow::bail!("Not a paged playlist view"),
    }
}

fn resume(session: &Session, request: &Browse, auth_hash: u64) -> Result<usize> {
    ensure!(
        session.auth_hash == auth_hash && session.browse_id == browse_id(request)?,
        Expired
    );
    offset(&request.cursor, session)
}

async fn fill<F, Fut>(session: &mut Session, start: usize, mut fetch: F) -> Result<()>
where
    F: FnMut(serde_json::Value) -> Fut,
    Fut: std::future::Future<Output = Result<serde_json::Value>>,
{
    // Fetch only enough to fill this UI batch. Retain upstream overflow for later.
    let mut fetched = 0;
    while session.tracks.len() < start + PAGE_SIZE {
        let Some(token) = session.next.clone() else {
            break;
        };
        ensure!(fetched < 4, "Too many empty upstream pages; retry");
        append(session, &fetch(json!({"continuation":token})).await?)?;
        fetched += 1;
    }
    Ok(())
}

pub async fn browse(
    config: &StreamConfig,
    request: &Browse,
    cache: &mut Cache,
) -> Result<(Page, Vec<Track>)> {
    let browse_id = browse_id(request)?;
    // Auth is reloaded on every page; do not mix two accounts after ytm -auth.
    let auth_hash = fingerprint(&std::fs::read(&config.auth_file)?);
    let client = InnerTubeClient::from_auth_path(&config.auth_file)?;
    let (mut session, start) = if request.cursor.is_empty() {
        let account = client.get_account_info().await?.account_name;
        let mut session = Session {
            generation: SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos(),
            auth_hash,
            browse_id: browse_id.clone(),
            account,
            tracks: Vec::new(),
            next: None,
            tokens: HashSet::new(),
        };
        append(
            &mut session,
            &client.post("browse", json!({"browseId":browse_id})).await?,
        )?;
        (session, 0)
    } else {
        let session = cache.session.as_ref().ok_or(Expired)?;
        (session.clone(), resume(session, request, auth_hash)?)
    };
    fill(&mut session, start, |body| async {
        Ok(client.post("browse", body).await?)
    })
    .await?;
    let result = page(&session, start);
    // Commit only a successful batch. Timeout/failure can safely retry the cursor.
    cache.session = Some(session);
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn session(count: usize) -> Session {
        Session {
            generation: 123,
            auth_hash: 0,
            browse_id: "VLLM".into(),
            account: "Test".into(),
            next: None,
            tokens: HashSet::new(),
            tracks: (0..count)
                .map(|i| Track {
                    id: format!("{i:011}"),
                    title: i.to_string(),
                    artist: "Artist".into(),
                    album: "Album".into(),
                })
                .collect(),
        }
    }
    fn request(view: &str, id: &str, cursor: &str) -> Browse {
        Browse {
            view: view.into(),
            id: id.into(),
            cursor: cursor.into(),
            query: String::new(),
        }
    }
    #[test]
    fn playlist_identity_aliases_and_cursor_binding() {
        assert_eq!(browse_id(&request("liked", "", "")).unwrap(), "VLLM");
        for id in ["LM", "VLLM"] {
            let request = request("playlist", id, "123:100");
            assert_eq!(browse_id(&request).unwrap(), "VLLM");
            assert_eq!(resume(&session(100), &request, 0).unwrap(), 100);
            assert!(resume(&session(100), &request, 1).is_err());
        }
        assert_eq!(
            browse_id(&request("playlist", "PLtest", "")).unwrap(),
            "VLPLtest"
        );
        assert!(resume(&session(100), &request("playlist", "PLother", "123:100"), 0).is_err());
        for id in ["", "https://example.test", "../../private"] {
            assert!(browse_id(&request("playlist", id, "")).is_err());
        }
        assert!(browse_id(&request("search", "LM", "")).is_err());
    }
    fn response(start: usize, count: usize, next: Option<&str>) -> serde_json::Value {
        let mut rows: Vec<_> = (start..start+count).map(|i| json!({"musicResponsiveListItemRenderer":{
            "flexColumns":[{"musicResponsiveListItemFlexColumnRenderer":{"text":{"runs":[{
                "text":format!("Song {i}"), "navigationEndpoint":{"watchEndpoint":{"videoId":format!("{i:011}")}}
            }]}}}]
        }})).collect();
        if let Some(token) = next {
            rows.push(json!({"continuationItemRenderer":{"continuationEndpoint":{"continuationCommand":{"token":token}}}}));
        }
        json!({"onResponseReceivedActions":[{"appendContinuationItemsAction":{"continuationItems":rows}}]})
    }
    #[tokio::test]
    async fn fetches_only_enough_for_requested_batch_and_reuses_overflow() {
        let mut cached = session(80);
        cached.next = Some("private-1".into());
        let mut requests = Vec::new();
        fill(&mut cached, 0, |body| {
            requests.push(body);
            std::future::ready(Ok(response(80, 150, Some("private-2"))))
        })
        .await
        .unwrap();
        assert_eq!(requests, vec![json!({"continuation":"private-1"})]);
        assert_eq!(page(&cached, 0).0.items.len(), 100);
        assert_eq!(page(&cached, 0).0.next_cursor.as_deref(), Some("123:100"));
        fill(&mut cached, 100, |_| async {
            panic!("Cached second batch must not fetch upstream")
        })
        .await
        .unwrap();
        assert_eq!(page(&cached, 100).0.items.len(), 100);
        fill(&mut cached, 200, |body| {
            requests.push(body);
            std::future::ready(Ok(response(230, 20, None)))
        })
        .await
        .unwrap();
        assert_eq!(requests.len(), 2);
        let last = page(&cached, 200).0;
        assert_eq!(last.items.len(), 50);
        assert!(last.next_cursor.is_none());
    }
    #[tokio::test]
    async fn failed_fetch_keeps_retryable_cached_session() {
        let mut original = session(100);
        original.next = Some("retry-token".into());
        let mut pending = original.clone();
        assert!(
            fill(&mut pending, 100, |_| async { anyhow::bail!("network") })
                .await
                .is_err()
        );
        assert_eq!(page(&original, 0).0.next_cursor.as_deref(), Some("123:100"));
        assert_eq!(original.next.as_deref(), Some("retry-token"));
    }
    #[test]
    fn exact_batches_remainder_and_retry() {
        let session = session(217);
        let (first, _) = page(&session, 0);
        assert_eq!(first.items.len(), 100);
        assert_eq!(first.next_cursor.as_deref(), Some("123:100"));
        let (second, _) = page(&session, offset("123:100", &session).unwrap());
        assert_eq!(second.items[0].id, "00000000100");
        assert_eq!(second.items.len(), 100);
        assert_eq!(page(&session, 100).0.items[0].id, second.items[0].id);
        let (last, _) = page(&session, 200);
        assert_eq!(last.items.len(), 17);
        assert!(last.next_cursor.is_none());
    }
    #[test]
    fn rejects_stale_forged_and_unaligned_cursors() {
        let session = session(100);
        for cursor in [
            "122:100",
            "123:200",
            "123:99",
            "123:0",
            "bad",
            "123:18446744073709551615",
        ] {
            assert!(offset(cursor, &session).is_err());
        }
        assert_eq!(offset("123:100", &session).unwrap(), 100);
    }
    #[test]
    fn upstream_remainder_or_token_keeps_next_page_available() {
        let mut cached = session(100);
        assert!(page(&cached, 0).0.next_cursor.is_none());
        cached.next = Some("private upstream token".into());
        assert_eq!(page(&cached, 0).0.next_cursor.as_deref(), Some("123:100"));
        assert!(page(&session(0), 0).0.items.is_empty());
    }
}
