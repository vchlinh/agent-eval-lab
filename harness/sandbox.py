"""
Sandbox: runs a command (normally pytest) for one task inside an isolated
Docker container — no network, capped CPU/memory, hard timeout.

This is where the agent's untrusted, LLM-generated code actually executes.
Nothing task-related ever runs as a bare subprocess on the host.
"""

from __future__ import annotations

import dataclasses
import subprocess
import time
import uuid

IMAGE_NAME = "agent-eval-lab-sandbox"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MEMORY = "512m"
DEFAULT_CPUS = "1"
DOCKERFILE_DIR = __file__.rsplit("/", 1)[0]


@dataclasses.dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class SandboxError(RuntimeError):
    """The sandbox infrastructure itself failed (not a test failure)."""


def build_image() -> None:
    """Build the sandbox image. Needs network once, at build time only."""
    proc = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, DOCKERFILE_DIR],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SandboxError(f"failed to build sandbox image:\n{proc.stderr}")


def _image_exists() -> bool:
    proc = subprocess.run(
        ["docker", "image", "inspect", IMAGE_NAME],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


class Sandbox:
    """
    One Sandbox = one task's isolated execution environment.

    Mounts `repo_dir` (the task's working copy on the host) read-write into
    a throwaway container per command. No network, capped memory/CPU/process
    count, and a hard wall-clock timeout that actually kills the container
    (not just the host-side docker CLI process) if exceeded.
    """

    def __init__(
        self,
        repo_dir: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        memory: str = DEFAULT_MEMORY,
        cpus: str = DEFAULT_CPUS,
    ):
        self.repo_dir = repo_dir
        self.timeout_seconds = timeout_seconds
        self.memory = memory
        self.cpus = cpus
        if not _image_exists():
            build_image()

    def run(self, command: list[str]) -> SandboxResult:
        container_name = f"agent-eval-{uuid.uuid4().hex[:12]}"
        docker_cmd = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--network", "none",
            "--memory", self.memory,
            "--cpus", self.cpus,
            "--pids-limit", "128",
            "-v", f"{self.repo_dir}:/workspace",
            "-w", "/workspace",
            IMAGE_NAME,
            *command,
        ]

        start = time.monotonic()
        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            # subprocess.run's timeout only kills the `docker run` CLI
            # process — the container keeps running in the daemon unless
            # we explicitly kill it by name.
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            return SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"[sandbox] timed out after {self.timeout_seconds}s",
                timed_out=True,
                duration_seconds=time.monotonic() - start,
            )

        return SandboxResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            timed_out=False,
            duration_seconds=time.monotonic() - start,
        )

    def run_tests(self, test_command: list[str] | None = None) -> SandboxResult:
        """Convenience wrapper: run pytest (or a custom command) in the sandbox."""
        return self.run(test_command or ["pytest", "-q"])
