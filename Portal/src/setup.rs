use crate::config::Config;
use anyhow::{Context, Result, ensure};
use std::{
    io::Write,
    os::unix::fs::{OpenOptionsExt, PermissionsExt},
    path::Path,
};

/// Generate private machine configuration once; never overwrite user settings.
pub fn configure(destination: &Path) -> Result<()> {
    if destination.exists() {
        let mut config = Config::load(destination)?;
        if config.stream.is_none() {
            config.stream = Some(stream_defaults()?);
            config.validate()?;
            let temporary = destination.with_extension("toml.new");
            let mut file = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(&temporary)?;
            file.write_all(toml::to_string_pretty(&config)?.as_bytes())?;
            file.sync_all()?;
            std::fs::rename(temporary, destination)?;
        }
        println!("Existing configuration preserved: {}", config.public_origin);
        return Ok(());
    }
    let output = std::process::Command::new("tailscale")
        .args(["status", "--json"])
        .output()?;
    ensure!(output.status.success(), "Tailscale status failed");
    let status: serde_json::Value = serde_json::from_slice(&output.stdout)?;
    ensure!(
        status["BackendState"].as_str() == Some("Running"),
        "Sign in to Tailscale first"
    );
    let dns = status["Self"]["DNSName"]
        .as_str()
        .context("Missing Tailscale DNS name")?
        .trim_end_matches('.');
    let user = status["Self"]["UserID"]
        .as_u64()
        .context("Missing Tailscale owner")?
        .to_string();
    let login = status["User"][&user]["LoginName"]
        .as_str()
        .context("Missing Tailscale login")?;
    let home = std::env::var("HOME")?;
    let runtime =
        std::env::var("XDG_RUNTIME_DIR").context("Run from the logged-in user's session")?;
    let mut config: Config = toml::from_str(include_str!("../config.example.toml"))?;
    config.music_root = Path::new(&home).join("storage/music");
    config.cmus_socket = Path::new(&runtime).join("cmus-socket");
    if let Some(stream) = &mut config.stream {
        stream.auth_file = Path::new(&home).join(".config/ytmusic-tui/browser.json");
        stream.mpv_socket = Path::new(&runtime).join("portal-stream/mpv.sock");
    }
    config.public_origin = format!("https://{dns}:8443");
    config.allowed_login = login.to_owned();
    config.validate()?;
    ensure!(config.music_root.is_dir(), "Storage music root is missing");
    let parent = destination
        .parent()
        .context("Missing configuration directory")?;
    std::fs::create_dir_all(parent)?;
    std::fs::set_permissions(parent, std::fs::Permissions::from_mode(0o700))?;
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(destination)?;
    file.write_all(toml::to_string_pretty(&config)?.as_bytes())?;
    file.sync_all()?;
    println!("Configured private Portal: {}", config.public_origin);
    Ok(())
}

fn stream_defaults() -> Result<crate::config::StreamConfig> {
    let template: Config = toml::from_str(include_str!("../config.example.toml"))?;
    let mut stream = template.stream.context("Missing Stream template")?;
    stream.auth_file = Path::new(&std::env::var("HOME")?).join(".config/ytmusic-tui/browser.json");
    stream.mpv_socket =
        Path::new(&std::env::var("XDG_RUNTIME_DIR")?).join("portal-stream/mpv.sock");
    Ok(stream)
}
