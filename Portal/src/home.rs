//! Home pages fetched on demand, with private, replayable server-side cursors.
use crate::{
    config::StreamConfig,
    home_parse::{self, Batch},
    library::Track,
    stream::{Browse, Expired, Page},
};
use anyhow::{Result, ensure};
use serde_json::json;
use std::{
    hash::{DefaultHasher, Hash, Hasher},
    time::{SystemTime, UNIX_EPOCH},
};
use ytmusic_api::InnerTubeClient;

#[derive(Default)]
pub struct Cache {
    session: Option<Session>,
}
struct Session {
    generation: u128,
    auth: u64,
    account: String,
    pages: Vec<Batch>,
}
fn fingerprint(bytes: &[u8]) -> u64 {
    let mut h = DefaultHasher::new();
    bytes.hash(&mut h);
    h.finish()
}
fn offset(cursor: &str, session: &Session) -> Result<usize> {
    ensure!(cursor.len() <= 64, "Invalid Home cursor");
    let (generation, index) = cursor
        .split_once(':')
        .ok_or_else(|| anyhow::anyhow!("Invalid Home cursor"))?;
    ensure!(generation.parse::<u128>()? == session.generation, Expired);
    let index = index.parse::<usize>()?;
    ensure!(
        index > 0 && index <= session.pages.len(),
        "Invalid Home offset"
    );
    Ok(index)
}
fn result(session: &Session, index: usize) -> (Page, Vec<Track>) {
    let batch = &session.pages[index];
    (
        Page {
            account: session.account.clone(),
            items: batch.items.clone(),
            next_cursor: batch
                .next
                .as_ref()
                .map(|_| format!("{}:{}", session.generation, index + 1)),
        },
        batch.tracks.clone(),
    )
}
pub async fn browse(
    config: &StreamConfig,
    request: &Browse,
    cache: &mut Cache,
) -> Result<(Page, Vec<Track>)> {
    let auth = fingerprint(&std::fs::read(&config.auth_file)?);
    let client = InnerTubeClient::from_auth_path(&config.auth_file)?;
    if request.cursor.is_empty() {
        let account = client.get_account_info().await?.account_name;
        let batch = home_parse::parse(
            &client
                .post("browse", json!({"browseId":"FEmusic_home"}))
                .await?,
        )?;
        let session = Session {
            generation: SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos(),
            auth,
            account,
            pages: vec![batch],
        };
        let page = result(&session, 0);
        cache.session = Some(session);
        return Ok(page);
    }
    let session = cache.session.as_mut().ok_or(Expired)?;
    ensure!(session.auth == auth, Expired);
    let index = offset(&request.cursor, session)?;
    if index < session.pages.len() {
        return Ok(result(session, index));
    }
    ensure!(index < 50, "Home pagination safety limit reached");
    let token = session
        .pages
        .last()
        .and_then(|p| p.next.as_ref())
        .ok_or_else(|| anyhow::anyhow!("Home exhausted"))?;
    let batch = home_parse::parse(&client.post("browse", json!({"continuation":token})).await?)?;
    if let Some(next) = &batch.next {
        ensure!(
            !session.pages.iter().any(|p| p.next.as_ref() == Some(next)),
            "Repeated Home continuation"
        )
    }
    ensure!(
        session.pages.iter().map(|p| p.items.len()).sum::<usize>() + batch.items.len() <= 10000,
        "Home cache safety limit reached"
    );
    session.pages.push(batch);
    Ok(result(session, index))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn cursors_are_bound_and_completed_pages_are_replayable() {
        let s = Session {
            generation: 123,
            auth: 0,
            account: "Test".into(),
            pages: vec![Batch {
                items: vec![],
                tracks: vec![],
                next: Some("private".into()),
            }],
        };
        assert_eq!(offset("123:1", &s).unwrap(), 1);
        for bad in ["122:1", "123:0", "123:2", "123:18446744073709551615", "bad"] {
            assert!(offset(bad, &s).is_err())
        }
        assert_eq!(result(&s, 0).0.next_cursor.as_deref(), Some("123:1"));
        assert_eq!(result(&s, 0).0.account, result(&s, 0).0.account);
    }
}
