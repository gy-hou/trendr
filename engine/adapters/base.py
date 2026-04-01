"""Abstract base class for platform adapters.

The adapter is the ONLY platform-specific code in TrendR v2.
Everything above it (state machine, validators, watchdog) is portable.

See ARCHITECTURE.md §2.1 for the full specification.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class PlatformAdapter(ABC):
    """Bridge between the research state machine and a specific LLM platform.

    Implementations:
        - OpenClawAdapter: sessions_spawn, web_fetch, exec
        - CLIAdapter:      subprocess + LLM API calls (standalone)

    Future (not in v2):
        - Claude Code source-level integration (separate project)
    """

    @abstractmethod
    def spawn_agent(self, agent_id: str, task: str, timeout_sec: int = 900) -> str:
        """Dispatch a sub-agent to perform a task.

        Args:
            agent_id: Agent identifier (e.g. "paper-scout", "paper-analyzer", "verifier")
            task: Full task description including skill references and file paths
            timeout_sec: Maximum wall-clock time before the agent is killed

        Returns:
            A handle string (session ID, process ID, etc.) for tracking.
        """
        ...

    @abstractmethod
    def await_agent(self, handle: str, poll_sec: int = 10) -> dict:
        """Block until the spawned agent completes.

        Args:
            handle: The handle returned by spawn_agent
            poll_sec: How often to check for completion

        Returns:
            {"status": "completed"|"failed"|"timeout", "output": str}
        """
        ...

    @abstractmethod
    def http_get(self, url: str, headers: Optional[dict] = None) -> dict:
        """Fetch a URL via HTTP GET.

        Args:
            url: The URL to fetch
            headers: Optional HTTP headers

        Returns:
            {"status_code": int, "body": str, "headers": dict}
        """
        ...

    @abstractmethod
    def read_file(self, path: Path) -> str:
        """Read a file's text content.

        Args:
            path: Absolute or project-relative path

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        ...

    @abstractmethod
    def write_file(self, path: Path, content: str) -> None:
        """Write text content to a file, creating parent directories as needed.

        Args:
            path: Absolute or project-relative path
            content: Text content to write
        """
        ...

    @abstractmethod
    def run_shell(self, command: str, timeout_sec: int = 30) -> dict:
        """Execute a shell command.

        Args:
            command: Shell command string
            timeout_sec: Maximum execution time

        Returns:
            {"exit_code": int, "stdout": str, "stderr": str}
        """
        ...

    @abstractmethod
    def send_heartbeat(self, project_dir: Path, state: dict) -> None:
        """Write a heartbeat signal for the watchdog.

        The default implementation writes heartbeat.json to project_dir.
        Platform adapters may add additional signaling (e.g. progress bars).

        Args:
            project_dir: The research project directory
            state: Current state dict with at least {agent, state, message}
        """
        ...

    @abstractmethod
    def browser_eval(self, js: str, url: Optional[str] = None) -> str:
        """Execute JavaScript in a browser context.

        Used by platform-hotspots skill for web scraping.

        Args:
            js: JavaScript code to evaluate
            url: Optional URL to navigate to before evaluating

        Returns:
            Stringified result of the JavaScript evaluation.
        """
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier.

        Returns:
            One of: 'openclaw', 'cli'
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} platform={self.platform_name}>"
