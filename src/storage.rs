use crate::{
    config::{Config, Storage},
    session::{Action, Session},
};
use anyhow::{Context, Result};
use serde_json::json;
use std::{
    fs::{create_dir_all, File, OpenOptions},
    io::{BufWriter, Write},
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

pub struct Log {
    writer: BufWriter<File>,
    pub path: PathBuf,
    written: usize,
    recorded: std::collections::BTreeSet<usize>,
}
impl Log {
    pub fn open(
        storage: &Storage,
        config: &Config,
        seed: u64,
        instrument: &str,
    ) -> Result<Option<Self>> {
        if !storage.enabled {
            return Ok(None);
        }
        let directory = match &storage.directory {
            Some(p) => p.clone(),
            None => match std::env::var_os("XDG_DATA_HOME") {
                Some(p) => PathBuf::from(p).join("utrp/practice"),
                None => PathBuf::from(
                    std::env::var_os("HOME").context("HOME or storage.directory required")?,
                )
                .join(".local/share/utrp/practice"),
            },
        };
        create_dir_all(&directory)
            .with_context(|| format!("create log directory {}", directory.display()))?;
        let stamp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos();
        let path = directory.join(format!("{stamp}-{}.jsonl", std::process::id()));
        let file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&path)?;
        let mut log = Self {
            writer: BufWriter::new(file),
            path,
            written: 0,
            recorded: std::collections::BTreeSet::new(),
        };
        log.write(
            &json!({"schema":1,"type":"start","seed":seed,"instrument":instrument,"config":config}),
        )?;
        Ok(Some(log))
    }
    fn write(&mut self, value: &serde_json::Value) -> Result<()> {
        serde_json::to_writer(&mut self.writer, value)?;
        writeln!(self.writer)?;
        self.writer.flush()?;
        Ok(())
    }
    pub fn update(&mut self, session: &Session, action: Action, now: u64) -> Result<()> {
        while self.written < session.history.len() {
            self.write(&json!({"type":"target","target":session.history[self.written]}))?;
            self.written += 1;
        }
        for (id, attempt) in session.attempts.iter().enumerate() {
            if let Some(attempt) = attempt {
                if !self.recorded.contains(&id) {
                    self.write(&json!({"type":"attempt","event_id":id,"attempt":attempt}))?;
                    self.recorded.insert(id);
                }
            }
        }
        self.write(&json!({"type":"action","at_ms":now,"action":action,"current":session.target().music.id,"seconds":session.seconds,"automatic":session.automatic,"paused":session.paused}))?;
        if session.stopped {
            self.write(&json!({"type":"summary","summary":session.summary(now),"attempts":session.attempts,"key_practice":session.key_practice()}))?;
        }
        Ok(())
    }
}
