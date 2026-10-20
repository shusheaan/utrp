use anyhow::{Context, Result, bail};
use serde::Serialize;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize)]
pub struct Track {
    pub id: String,
    pub artist: String,
    pub album: String,
    pub title: String,
}

pub fn scan(root: &Path) -> Result<Vec<Track>> {
    let root = root.canonicalize().context("Music root unavailable")?;
    let mut paths = Vec::new();
    collect(&root, &mut paths)?;
    paths.sort();
    paths.iter().map(|path| track(&root, path)).collect()
}

fn collect(directory: &Path, output: &mut Vec<PathBuf>) -> Result<()> {
    for entry in directory.read_dir()? {
        let entry = entry?;
        let kind = entry.file_type()?;
        // Never follow links out of the music root or into a directory cycle.
        if kind.is_dir() {
            collect(&entry.path(), output)?;
        } else if kind.is_file() && supported(&entry.path()) {
            output.push(entry.path());
        }
    }
    Ok(())
}

fn supported(path: &Path) -> bool {
    path.extension()
        .and_then(|v| v.to_str())
        .is_some_and(|ext| {
            matches!(
                ext.to_ascii_lowercase().as_str(),
                "flac" | "mp3" | "m4a" | "opus" | "ogg" | "wav" | "aac"
            )
        })
}

fn track(root: &Path, path: &Path) -> Result<Track> {
    let relative = path
        .strip_prefix(root)?
        .to_str()
        .context("Non-UTF8 music filename")?;
    if relative.contains(['\n', '\r', '\0']) {
        bail!("Music filenames must not contain command delimiters");
    }
    let parts: Vec<&str> = relative.split('/').collect();
    let title = path
        .file_stem()
        .and_then(|v| v.to_str())
        .context("Invalid track filename")?;
    Ok(Track {
        id: relative.to_owned(),
        artist: if parts.len() >= 2 {
            parts[0]
        } else {
            "Unknown artist"
        }
        .to_owned(),
        album: if parts.len() >= 3 {
            parts[1]
        } else {
            "Singles"
        }
        .to_owned(),
        title: title.to_owned(),
    })
}

pub fn resolve(root: &Path, tracks: &[Track], id: &str) -> Result<PathBuf> {
    if !tracks.iter().any(|track| track.id == id) {
        bail!("Track is not in the library");
    }
    let path = root.join(id).canonicalize()?;
    if !path.starts_with(root) || !path.is_file() {
        bail!("Track moved outside the library");
    }
    Ok(path)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sorted_library_ignores_links_and_rejects_unknown_paths() {
        let tmp = tempfile::tempdir().unwrap();
        let album = tmp.path().join("Artist/Album");
        std::fs::create_dir_all(&album).unwrap();
        for name in ["02 B.flac", "01 A.flac", "cover.jpg"] {
            std::fs::write(album.join(name), []).unwrap();
        }
        std::os::unix::fs::symlink("/etc", tmp.path().join("outside")).unwrap();
        let tracks = scan(tmp.path()).unwrap();
        assert_eq!(tracks.len(), 2);
        assert_eq!(tracks[0].title, "01 A");
        assert_eq!(tracks[0].artist, "Artist");
        assert!(resolve(tmp.path(), &tracks, "../../etc/passwd").is_err());
        assert!(resolve(tmp.path(), &tracks, &tracks[0].id).is_ok());
        std::fs::remove_file(album.join("01 A.flac")).unwrap();
        std::os::unix::fs::symlink("/etc/passwd", album.join("01 A.flac")).unwrap();
        assert!(resolve(tmp.path(), &tracks, &tracks[0].id).is_err());
    }

    #[test]
    fn command_delimiter_is_rejected() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("bad\nquit.flac"), []).unwrap();
        assert!(scan(tmp.path()).is_err());
    }
}
