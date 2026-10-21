// Explicit, temporary maintenance helper. Never load from the production controllers.
function scheduleLibraryLevels(host, config, apply) {
    const app = host.createApplication();
    const project = app.projectName();
    const recording = host.createTransport().isArrangerRecordEnabled();
    [project, recording].forEach(v => v.markInterested());
    const bank = host.createTrackBank(config.capacity, 0, 0, true);
    bank.setContentFilter(Java.type('com.bitwig.extension.controller.api.TrackBankContentFilter').ALL_CHANNELS);
    bank.setSkipDisabledItems(false);
    const tracks = [];
    const master = host.createMasterTrack(0);
    function observe(track) {
        [track.name(), track.exists(), track.trackType(), track.volume(), track.volume().displayedValue(),
            track.arm(), track.monitorMode(), track.isActivated(), track.mute(), track.pan()].forEach(v => v.markInterested());
        return track;
    }
    for (let i = 0; i < config.capacity; i++) tracks.push(observe(bank.getItemAt(i)));
    observe(master);
    function state(t) {
        return JSON.stringify([t.arm().get(), t.monitorMode().get(), t.isActivated().get(), t.mute().get(), t.pan().get()]);
    }
    function target(t) {
        if (config.preserve.includes(t.name().get())) return null;
        return ['Master', 'Group'].includes(t.trackType().get()) || config.unity.includes(t.name().get())
            ? config.bus_db : config.sound_db;
    }
    function valid() {
        return project.get() === config.project && !recording.get() &&
            tracks[0].name().get() === config.signature && !tracks[config.capacity - 1].exists().get();
    }
    function run() {
        if (!valid()) { println('LEVELS ABORT: wrong project, recording, signature or capacity'); return; }
        const live = tracks.filter(t => t.exists().get());
        if (!live.some(t => t.trackType().get() === 'Master')) live.push(master);
        if (!master.exists().get() || config.preserve.some(name => !live.some(t => t.name().get() === name))) {
            println('LEVELS ABORT: missing master or protected track'); return;
        }
        const before = live.map(t => ({name: t.name().get(), raw: t.volume().getRaw(), state: state(t)}));
        before.forEach((v, i) => println('LEVELS BEFORE ' + JSON.stringify({...v, db: live[i].volume().displayedValue().get()})));
        if (apply) live.forEach(t => {
            const db = target(t);
            if (db !== null) t.volume().setRaw(Math.pow(10, db / config.raw_db_scale));
        });
        host.scheduleTask(() => {
            if (!valid()) { println('LEVELS VERIFY ABORT: context changed'); return; }
            const errors = [];
            live.forEach((t, i) => {
                const db = target(t), display = t.volume().displayedValue().get();
                if (t.name().get() !== before[i].name || state(t) !== before[i].state) errors.push(t.name().get() + ': non-volume state changed');
                if (db === null && t.volume().getRaw() !== before[i].raw) errors.push(t.name().get() + ': protected volume changed');
                if (db !== null && (!Number.isFinite(parseFloat(display)) || Math.abs(parseFloat(display) - db) > config.verify_tolerance_db)) errors.push(t.name().get() + ': ' + display);
            });
            errors.forEach(e => println('LEVELS ERROR ' + e));
            const protectedCount = live.filter(t => target(t) === null).length;
            println('LEVELS ' + (errors.length ? 'FAIL' : 'PASS') + ': inspected=' + live.length +
                ' protected=' + protectedCount + ' errors=' + errors.length + ' mode=' + (apply ? 'apply' : 'verify'));
            println('LEVELS TARGET: sounds=' + config.sound_db + ' dB, groups/master=' + config.bus_db + ' dB');
            app.getAction('show_controller_script_console').invoke();
        }, 1200);
    }
    host.scheduleTask(run, 2500);
}
