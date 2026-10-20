//! Playback effect state. No browser clocks, filesystem or player I/O.
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Source {
    Local,
    Stream,
}
impl Source {
    pub fn index(self) -> usize {
        match self {
            Self::Local => 0,
            Self::Stream => 1,
        }
    }
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct View {
    pub fade: bool,
    pub forced: bool,
    pub a: Option<f64>,
    pub b: Option<f64>,
    pub error: Option<&'static str>,
}

#[derive(Debug)]
pub struct Snapshot {
    pub track: Option<String>,
    pub position: f64,
    pub duration: f64,
    pub playing: bool,
    pub coarse: bool,
}

#[derive(Debug)]
pub struct Player {
    pub preference: bool,
    pub a: Option<f64>,
    pub b: Option<f64>,
    pub track: Option<String>,
    pub volume: u8,
    pub error: Option<&'static str>,
    pub retry_in: f64,
    last_raw: f64,
    fraction: f64,
    last_position: f64,
    pub attack: f64,
    pub pending_seek: Option<f64>,
    seek_wait: f64,
    manual_pending: bool,
    loop_suspended: bool,
}
impl Default for Player {
    fn default() -> Self {
        Self {
            preference: false,
            a: None,
            b: None,
            track: None,
            volume: 100,
            error: None,
            retry_in: 0.0,
            last_raw: 0.0,
            fraction: 0.0,
            last_position: 0.0,
            attack: 0.0,
            pending_seek: None,
            seek_wait: 0.0,
            manual_pending: false,
            loop_suspended: false,
        }
    }
}
impl Player {
    pub fn view(&self) -> View {
        View {
            fade: self.enabled(),
            forced: self.b.is_some(),
            a: self.a,
            b: self.b,
            error: self.error,
        }
    }
    pub fn enabled(&self) -> bool {
        self.preference || self.b.is_some()
    }
    pub fn needs_tick(&self) -> bool {
        self.enabled() || self.a.is_some() || self.volume != 100
    }
    pub fn clear(&mut self) {
        self.a = None;
        self.b = None;
        self.loop_suspended = false;
        self.manual_pending = false;
        self.pending_seek = None;
        self.seek_wait = 0.0;
    }
    pub fn observe(&mut self, snapshot: &Snapshot) {
        if self.track != snapshot.track {
            self.clear();
            self.track = snapshot.track.clone();
            self.restart(snapshot.position);
        }
    }
    pub fn restart(&mut self, position: f64) {
        self.attack = 0.0;
        self.last_raw = position;
        self.last_position = position;
        self.fraction = 0.0;
    }
    pub fn range(&self) -> Option<(f64, f64)> {
        self.a.zip(self.b).map(|(a, b)| (a.min(b), a.max(b)))
    }
    pub fn mark(&mut self, position: f64) -> Result<Option<f64>, &'static str> {
        match (self.a, self.b) {
            (_, Some(_)) => {
                self.clear();
                Ok(None)
            }
            (None, _) => {
                self.a = Some(position);
                Ok(None)
            }
            (Some(a), None) => {
                if (a - position).abs() < 1.0 {
                    return Err("A and B must be at least one second apart.");
                }
                self.b = Some(position);
                let start = a.min(position);
                self.seek_started(start);
                Ok(Some(start))
            }
        }
    }
    pub fn seek_started(&mut self, position: f64) {
        self.manual_pending = false;
        self.restart(position);
        self.pending_seek = Some(position);
        self.seek_wait = 0.0;
    }
    /// Manual transport never changes A/B. Outside the range, let the user listen
    /// freely until playback enters the marked range again.
    pub fn manual_seek(&mut self, position: f64) {
        self.seek_started(position);
        if !self.enabled() {
            self.pending_seek = None;
            return;
        }
        self.manual_pending = true;
        self.loop_suspended = self
            .range()
            .is_some_and(|(a, b)| position < a || position >= b);
    }
    pub fn tick(&mut self, snapshot: &Snapshot, dt: f64, fade_seconds: f64) -> (u8, Option<f64>) {
        self.observe(snapshot);
        if !self.enabled() {
            return (100, None);
        }
        if snapshot.track.is_none() {
            return (0, None);
        }
        if let Some(target) = self.pending_seek {
            self.seek_wait += dt;
            if (snapshot.position - target).abs() <= 1.0 {
                self.pending_seek = None;
                self.restart(snapshot.position);
                if self.manual_pending {
                    self.attack = fade_seconds;
                    self.manual_pending = false;
                }
            } else if self.seek_wait < 2.0 {
                return (if self.manual_pending { 100 } else { 0 }, None);
            } else if self.manual_pending {
                self.pending_seek = None;
                self.manual_pending = false;
                self.loop_suspended = true;
                self.error = Some("Manual seek was not confirmed. A/B markers were kept.");
                return (100, None);
            } else {
                self.clear();
                self.preference = false;
                self.error = Some("AB seek failed. Loop disabled.");
                return (100, None);
            }
        }
        if !snapshot.playing {
            return (self.volume, None);
        }
        let position = self.position(snapshot, dt);
        if position + 0.5 < self.last_position {
            self.attack = 0.0;
        }
        self.last_position = position;
        self.attack += dt;
        if self.loop_suspended
            && self
                .range()
                .is_some_and(|(a, b)| position >= a && position < b)
        {
            self.loop_suspended = false;
        }
        let range = self.range().filter(|_| !self.loop_suspended);
        let (start, end) = range.unwrap_or((0.0, snapshot.duration));
        if range.is_some() && (position >= end || position + 0.2 < start) {
            self.seek_started(start);
            return (0, Some(start));
        }
        let length = (end - start).max(0.0);
        let fade = fade_seconds.min(length / 3.0).max(0.05);
        // Equal-power crossfade is not intended: one player, sequential fades.
        let tail = if end > 0.0 {
            ((end - position) / fade).clamp(0.0, 1.0)
        } else {
            1.0
        };
        let gain = (self.attack / fade).clamp(0.0, 1.0).min(tail);
        ((gain * 100.0).round() as u8, None)
    }
    fn position(&mut self, snapshot: &Snapshot, dt: f64) -> f64 {
        if !snapshot.coarse {
            return snapshot.position;
        }
        if snapshot.position != self.last_raw {
            self.last_raw = snapshot.position;
            self.fraction = 0.0;
        } else {
            self.fraction = (self.fraction + dt).min(0.95);
        }
        snapshot.position + self.fraction
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn snap(position: f64) -> Snapshot {
        Snapshot {
            track: Some("song".into()),
            position,
            duration: 100.0,
            playing: true,
            coarse: false,
        }
    }
    #[test]
    fn reversed_marks_force_fade_and_restore_preference() {
        for preference in [false, true] {
            let mut p = Player {
                preference,
                ..Player::default()
            };
            p.mark(20.0).unwrap();
            assert_eq!(p.view().fade, preference);
            assert_eq!(p.mark(10.0).unwrap(), Some(10.0));
            assert_eq!(p.range(), Some((10.0, 20.0)));
            assert!(p.view().forced && p.view().fade);
            assert_eq!(p.a, Some(20.0));
            p.mark(15.0).unwrap();
            assert_eq!(p.view().fade, preference);
            assert!(!p.view().forced);
        }
    }
    #[test]
    fn invalid_b_preserves_a() {
        let mut p = Player::default();
        p.mark(10.0).unwrap();
        assert!(p.mark(10.5).is_err());
        assert_eq!(p.a, Some(10.0));
        assert_eq!(p.b, None);
    }
    #[test]
    fn loop_seeks_and_short_ranges_reach_full_volume() {
        let mut p = Player::default();
        p.observe(&snap(10.0));
        p.mark(10.0).unwrap();
        p.mark(11.5).unwrap();
        assert_eq!(p.tick(&snap(10.0), 0.05, 2.5).1, None);
        assert_eq!(p.tick(&snap(10.6), 0.6, 2.5).0, 100);
        assert!(p.tick(&snap(11.4), 0.05, 2.5).0 < 30);
        assert_eq!(p.tick(&snap(11.5), 0.05, 2.5), (0, Some(10.0)));
        assert!(p.tick(&snap(10.0), 0.05, 2.5).0 < 20);
    }
    #[test]
    fn track_change_clears_loop_and_natural_repeat_restarts_fade() {
        let mut p = Player {
            preference: true,
            ..Player::default()
        };
        p.tick(&snap(97.5), 3.0, 2.5);
        assert_eq!(p.tick(&snap(99.5), 0.05, 2.5).0, 20);
        assert!(p.tick(&snap(0.0), 0.05, 2.5).0 < 5);
        p.mark(1.0).unwrap();
        p.mark(5.0).unwrap();
        let mut next = snap(0.0);
        next.track = Some("next".into());
        p.tick(&next, 0.05, 2.5);
        assert!(p.a.is_none() && p.b.is_none());
        assert!(p.preference);
    }
    #[test]
    fn stalled_seek_disables_loop_and_restores_volume() {
        let mut p = Player::default();
        p.observe(&snap(20.0));
        p.mark(10.0).unwrap();
        p.mark(20.0).unwrap();
        assert_eq!(p.tick(&snap(20.0), 0.1, 2.5), (0, None));
        assert_eq!(p.tick(&snap(20.0), 2.0, 2.5), (100, None));
        assert!(p.error.is_some());
    }
    #[test]
    fn manual_scrubbing_preserves_marks_and_allows_outside_playback() {
        for target in [5.0, 15.0, 30.0] {
            let mut p = Player::default();
            p.observe(&snap(10.0));
            p.mark(10.0).unwrap();
            p.mark(20.0).unwrap();
            p.manual_seek(target);
            assert_eq!(p.tick(&snap(target), 0.05, 0.75), (100, None));
            assert_eq!((p.a, p.b), (Some(10.0), Some(20.0)));
            assert_eq!(p.tick(&snap(target + 1.0), 0.05, 0.75).1, None);
            // Re-entering the original range resumes looping without moving markers.
            p.manual_seek(15.0);
            p.tick(&snap(15.0), 0.05, 0.75);
            assert_eq!(p.tick(&snap(20.0), 0.05, 0.75), (0, Some(10.0)));
        }
    }
    #[test]
    fn manual_seek_during_pending_ab_seek_does_not_clear_marks() {
        let mut p = Player::default();
        p.observe(&snap(10.0));
        p.mark(10.0).unwrap();
        p.mark(20.0).unwrap();
        p.manual_seek(40.0);
        assert_eq!(p.tick(&snap(10.0), 0.1, 0.75), (100, None));
        assert_eq!(p.tick(&snap(40.0), 0.1, 0.75), (100, None));
        assert_eq!(p.range(), Some((10.0, 20.0)));
    }
    #[test]
    fn short_default_fade_reaches_full_volume_in_under_one_second() {
        let mut p = Player {
            preference: true,
            ..Player::default()
        };
        assert_eq!(p.tick(&snap(0.0), 0.375, 0.75).0, 50);
        assert_eq!(p.tick(&snap(0.375), 0.375, 0.75).0, 100);
    }
    #[test]
    fn pause_does_not_advance_or_seek() {
        let mut p = Player {
            preference: true,
            ..Player::default()
        };
        p.tick(&snap(12.0), 1.0, 2.5);
        let attack = p.attack;
        let mut paused = snap(12.0);
        paused.playing = false;
        assert_eq!(p.tick(&paused, 30.0, 2.5).1, None);
        assert_eq!(p.attack, attack);
    }
}
