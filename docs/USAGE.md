# Usage

## Installation
```bash
git clone https://github.com/gy-hou/trendr.git
cd trendr
chmod +x install.sh
./install.sh
```

## Quick start
```bash
python3 cli.py run --topic "agent swarm systems" --platform codex
```

## Inputs
- `--topic`: required, research topic.
- `--platform`: recommended, explicit runtime selection.
- `--depth`: `A|B|C`, depth level.
- `--project-dir`: optional, output directory.

## Basic commands
- Start run:
```bash
python3 cli.py run --topic "<topic>" --platform codex
```

- Check status:
```bash
python3 cli.py status <project_dir>
```

- Resume run:
```bash
python3 cli.py resume <project_dir> --platform codex
```

- Optional hotspots command:
```bash
python3 cli.py hotspots --project-dir <dir>
```

## Run modes
- `--profile basic`: standard pipeline.
- `--profile full`: extended execution path.
- `--profile lite`: lightweight path.

## Examples
```bash
python3 cli.py run --topic "agentic rag systems" --depth B --platform codex
python3 cli.py run --topic "rl market making" --depth A --platform cli --project-dir ~/research/rl-mm
python3 cli.py resume ~/research/rl-mm --platform cli
```
