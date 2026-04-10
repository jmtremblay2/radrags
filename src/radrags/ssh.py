"""SSH client for remote command execution."""

from __future__ import annotations

import os
from dataclasses import dataclass

import paramiko


@dataclass
class CommandResult:
    """Result of a remote command execution."""

    stdout: str
    stderr: str
    exit_code: int


class SSHClient:
    """SSH client for executing commands on a remote host.

    Args:
        host: SSH hostname or IP.
        port: SSH port.
        user: SSH username.
        key_path: Path to the SSH private key file.
    """

    def __init__(self, host: str, port: int, user: str, key_path: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._key_path = os.path.expanduser(key_path)
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._client.connect(
                hostname=host,
                port=port,
                username=user,
                key_filename=self._key_path,
            )
        except (
            paramiko.ssh_exception.NoValidConnectionsError,
            paramiko.ssh_exception.SSHException,
            OSError,
        ) as exc:
            raise ConnectionError(f"SSH connection to {host}:{port} failed: {exc}")

    def execute(self, cmd: str) -> CommandResult:
        """Execute a command on the remote host.

        Args:
            cmd: The shell command to run.

        Returns:
            A ``CommandResult`` with stdout, stderr, and exit code.
        """
        _, stdout, stderr = self._client.exec_command(cmd)
        return CommandResult(
            stdout=stdout.read().decode(),
            stderr=stderr.read().decode(),
            exit_code=stdout.channel.recv_exit_status(),
        )

    def close(self) -> None:
        """Close the SSH connection."""
        self._client.close()
