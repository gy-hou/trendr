"""Resume-request helpers."""

from pathlib import Path

from engine.artifacts.io import read_json


def consume_resume_request(project_dir: Path) -> dict | None:
    path = project_dir / "resume_request.json"
    payload = read_json(path)
    if payload is None:
        return None
    try:
        path.unlink()
    except OSError:
        return None
    return payload
