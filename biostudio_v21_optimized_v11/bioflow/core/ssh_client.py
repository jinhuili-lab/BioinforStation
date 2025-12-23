from typing import Optional
import paramiko

class SSHClient:
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None

    def connect(self, host: str, port: int, username: str, password: str | None = None, key_filename: str | None = None):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_filename:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                key_filename=key_filename,
                allow_agent=True,
                look_for_keys=True,
                timeout=10,
            )
        else:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                allow_agent=True,
                look_for_keys=True,
                timeout=10,
            )
        self.client = client

    def exec(self, command: str) -> tuple[str, str, int]:
        if not self.client:
            raise RuntimeError("Not connected")
        stdin, stdout, stderr = self.client.exec_command(command)
        out = stdout.read().decode()
        err = stderr.read().decode()
        code = stdout.channel.recv_exit_status()
        return out, err, code

    # ---- Interactive shell (MobaXterm style) ----
    def open_shell(self, term: str = "xterm", width: int = 120, height: int = 32):
        if not self.client:
            raise RuntimeError("Not connected")
        # Close old channel if exists
        if self.channel is not None:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None
        transport = self.client.get_transport()
        if transport is None or not transport.is_active():
            raise RuntimeError("SSH transport is not active")
        chan = transport.open_session()
        # Request a PTY so that we get real terminal behavior (like MobaXterm)
        chan.get_pty(term=term, width=width, height=height)
        chan.invoke_shell()
        chan.settimeout(0.0)
        self.channel = chan
        return chan

    def shell_send(self, data: str):
        if self.channel is None:
            raise RuntimeError("Shell not open")
        # Paramiko expects bytes-like, but accepts str directly
        self.channel.send(data)

    def shell_recv(self, bufsize: int = 4096) -> str:
        if self.channel is None:
            return ""
        if self.channel.recv_ready():
            return self.channel.recv(bufsize).decode(errors="ignore")
        return ""

    def close_shell(self):
        if self.channel is not None:
            try:
                self.channel.close()
            except Exception:
                pass
            self.channel = None

    def close(self):
        self.close_shell()
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
