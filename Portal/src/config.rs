use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::{net::SocketAddr, path::PathBuf, time::Duration};

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    #[serde(default = "default_fade_seconds")]
    pub fade_seconds: f64,
    #[serde(default)]
    pub stream: Option<StreamConfig>,
    pub listen: SocketAddr,
    pub music_root: PathBuf,
    pub cmus_socket: PathBuf,
    pub public_origin: String,
    pub allowed_login: String,
    pub request_timeout_seconds: u64,
}

fn default_fade_seconds() -> f64 {
    0.75
}

impl Config {
    pub fn load(path: &std::path::Path) -> Result<Self> {
        let mut config: Self = toml::from_str(&std::fs::read_to_string(path)?)?;
        config.validate()?;
        config.music_root = config
            .music_root
            .canonicalize()
            .context("Music root unavailable")?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.fade_seconds.is_finite() && (0.1..=5.0).contains(&self.fade_seconds),
            "Fade duration must be 0.1 to 5 seconds"
        );
        ensure!(
            self.listen.ip().is_loopback(),
            "Portal must listen on loopback only"
        );
        ensure!(
            self.cmus_socket.is_absolute(),
            "CMUS socket must be absolute"
        );
        ensure!(
            !self.allowed_login.trim().is_empty(),
            "Tailscale login is required"
        );
        ensure!(
            (1..=30).contains(&self.request_timeout_seconds),
            "Invalid command timeout"
        );
        let uri: axum::http::Uri = self.public_origin.parse()?;
        ensure!(
            uri.scheme_str() == Some("https") && uri.authority().is_some(),
            "HTTPS origin required"
        );
        ensure!(
            uri.path() == "/" && uri.query().is_none() && !self.public_origin.ends_with('/'),
            "Origin must not include a path"
        );
        if let Some(stream) = &self.stream {
            ensure!(
                stream.auth_file.is_absolute() && stream.mpv_socket.is_absolute(),
                "Stream paths must be absolute"
            );
            ensure!(
                (5..=120).contains(&stream.fetch_timeout_seconds),
                "Invalid Stream fetch timeout"
            );
            ensure!(
                (1..=5000).contains(&stream.list_limit),
                "Invalid Stream list limit"
            );
        }
        Ok(())
    }

    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.request_timeout_seconds)
    }
}

#[derive(Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct StreamConfig {
    pub auth_file: PathBuf,
    pub mpv_socket: PathBuf,
    pub fetch_timeout_seconds: u64,
    pub list_limit: usize,
}
