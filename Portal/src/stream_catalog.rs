//! Search and artist-page adapters over the pinned owner's API.
use crate::{
    library::Track,
    stream::{Item, playlist_item, track_item, valid_id},
};
use ytmusic_api::{AlbumInfo, ArtistInfo, RelatedArtist, SearchResults};

// Default search skips the upstream best-match card. Filtered shelves include
// that match and preserve the server's category-specific relevance ordering.
pub async fn search(
    client: &ytmusic_api::InnerTubeClient,
    query: &str,
    limit: usize,
) -> anyhow::Result<SearchResults> {
    let (songs, artists, albums, playlists) = tokio::try_join!(
        client.search_all(query, limit, Some("songs")),
        client.search_all(query, limit, Some("artists")),
        client.search_all(query, limit, Some("albums")),
        client.search_all(query, limit, Some("playlists")),
    )?;
    Ok(SearchResults {
        tracks: songs.tracks,
        artists: artists.artists,
        albums: albums.albums,
        playlists: playlists.playlists,
    })
}
pub fn album_item(a: AlbumInfo, section: &str) -> Option<Item> {
    (valid_id(&a.browse_id) && !a.title.trim().is_empty()).then(|| Item {
        kind: "album",
        id: a.browse_id,
        title: a.title,
        subtitle: a.artist,
        section: section.into(),
    })
}
pub fn artist_item(a: RelatedArtist, section: &str) -> Option<Item> {
    (valid_id(&a.channel_id) && !a.name.trim().is_empty()).then(|| Item {
        kind: "artist",
        id: a.channel_id,
        title: a.name,
        subtitle: "Artist".into(),
        section: section.into(),
    })
}
pub fn search_items(results: SearchResults, tracks: &mut Vec<Track>) -> Vec<Item> {
    let mut items: Vec<Item> = results
        .tracks
        .into_iter()
        .filter_map(|t| track_item(t, "Songs", tracks))
        .collect();
    items.extend(
        results
            .artists
            .into_iter()
            .filter_map(|a| artist_item(a, "Artists")),
    );
    items.extend(
        results
            .albums
            .into_iter()
            .filter_map(|a| album_item(a, "Albums")),
    );
    items.extend(
        results
            .playlists
            .into_iter()
            .filter(|p| valid_id(&p.playlist_id) && !p.title.trim().is_empty())
            .map(|p| playlist_item(p, "Playlists")),
    );
    items
}
pub fn artist_items(artist: ArtistInfo, tracks: &mut Vec<Track>) -> Vec<Item> {
    let mut items: Vec<Item> = artist
        .top_songs
        .into_iter()
        .filter_map(|t| track_item(t, "Top songs", tracks))
        .collect();
    items.extend(
        artist
            .albums
            .into_iter()
            .filter_map(|a| album_item(a, "Albums")),
    );
    items.extend(
        artist
            .related_artists
            .into_iter()
            .filter_map(|a| artist_item(a, "Similar artists")),
    );
    items
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn all_search_types_are_routable_and_only_songs_are_playable() {
        let results = SearchResults {
            tracks: vec![ytmusic_api::Track::new_minimal(
                "abcdefghijk",
                "Song",
                "Artist",
            )],
            artists: vec![RelatedArtist::new("UCartist", "Artist", "")],
            albums: vec![AlbumInfo::new_without_tracks(
                "MPREalbum",
                "Album",
                "Artist",
                "",
                "",
            )],
            playlists: vec![ytmusic_api::PlaylistInfo::new(
                "PLplaylist",
                "Playlist",
                "",
                0,
                "",
            )],
        };
        let mut tracks = Vec::new();
        let items = search_items(results, &mut tracks);
        assert_eq!(
            items.iter().map(|i| i.kind).collect::<Vec<_>>(),
            vec!["track", "artist", "album", "playlist"]
        );
        assert_eq!(tracks.len(), 1);
        assert!(artist_item(RelatedArtist::new("https://bad", "Bad", ""), "").is_none());
        assert!(artist_item(RelatedArtist::new("UCblank", " ", ""), "").is_none());
        assert!(
            album_item(
                AlbumInfo::new_without_tracks("MPREblank", "", "", "", ""),
                ""
            )
            .is_none()
        );
    }
    #[test]
    fn artist_page_includes_songs_albums_and_similar_artists() {
        let artist = ArtistInfo::new(
            "UCone",
            "One",
            "",
            vec![ytmusic_api::Track::new_minimal(
                "abcdefghijk",
                "Song",
                "One",
            )],
            vec![AlbumInfo::new_without_tracks(
                "MPREone", "Album", "One", "", "",
            )],
            vec![RelatedArtist::new("UCtwo", "Two", "")],
            "",
        );
        let items = artist_items(artist, &mut Vec::new());
        assert_eq!(
            items.iter().map(|i| i.section.as_str()).collect::<Vec<_>>(),
            vec!["Top songs", "Albums", "Similar artists"]
        );
    }
}
