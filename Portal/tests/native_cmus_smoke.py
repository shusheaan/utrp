"""Private CMUS instance, temporary HOME, ALSA null device and silent fixture only."""
from pathlib import Path
import os
import errno
import fcntl
import termios
import struct
import threading
import pty
import select
import socket
import subprocess
import tempfile
import time
import wave


def command(path: Path, text: str) -> str:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(2)
        client.connect(str(path))
        client.sendall((text + '\n').encode())
        data = b''
        while data != b'\n' and not data.endswith(b'\n\n'):
            chunk = client.recv(65536)
            if not chunk:
                raise RuntimeError('CMUS closed the IPC connection')
            data += chunk
        result = data.decode()
        assert not result.startswith('error '), result
        return result


def run() -> None:
    with tempfile.TemporaryDirectory(prefix='portal-cmus-check-') as temporary:
        root = Path(temporary)
        config = root / 'config/cmus'
        config.mkdir(parents=True)
        (config / 'autosave').write_text('set output_plugin=alsa\nset dsp.alsa.device=null\nset softvol=true\nset repeat=true\nset repeat_current=true\n')
        audio = root / 'silence.wav'
        with wave.open(str(audio), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(bytes(8000 * 2 * 30))
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH",24,80,0,0))
        ipc = root / 'cmus.sock'
        process = subprocess.Popen(['cmus', '--listen', str(ipc)], stdin=slave, stdout=slave, stderr=slave,
                                   env=dict(os.environ, HOME=str(root), XDG_CONFIG_HOME=str(root/'config'), CMUS_HOME=str(config), TERM='xterm-256color'))
        os.close(slave)
        def drain() -> None:
            while process.poll() is None:
                if select.select([master],[],[],.05)[0]:
                    try:
                        os.read(master,65536)
                    except OSError as error:
                        if error.errno in (errno.EIO, errno.EBADF):
                            return
                        raise
        reader = threading.Thread(target=drain,daemon=True)
        reader.start()
        try:
            for _ in range(100):
                if ipc.exists():
                    break
                time.sleep(.02)
            assert ipc.exists(), 'Private CMUS did not start'
            time.sleep(.2)
            os.write(master,b'\n')  # Private-instance MPRIS name conflict acknowledgement.
            time.sleep(.2)
            command(ipc, 'set softvol=true')
            command(ipc, 'vol 37%')
            status = command(ipc, 'status')
            assert 'set vol_left 37' in status and 'set vol_right 37' in status, status
            command(ipc, f'player-play {audio}')
            command(ipc, 'player-pause')
            command(ipc, 'seek 12')
            status = command(ipc, 'status')
            assert 'status paused' in status and 'position 12' in status, status
            command(ipc, 'vol 100%')
            status = command(ipc, 'status')
            assert 'set vol_left 100' in status and 'set vol_right 100' in status, status
            command(ipc, 'player-stop')
            print('PASS: actual isolated CMUS accepts software-only 37%/100% gain and absolute seek while paused; no user audio/session changed')
        finally:
            process.terminate()
            process.wait(timeout=5)
            os.close(master)


if __name__ == '__main__':
    run()
