---
description: "Initialize TrendR hotspots template + private config"
argument-hint: "[--force]"
allowed-tools: Bash
---

Run:
```
Bash: python {{repo_root}}/cli.py hotspots-template $ARGUMENTS
```

Report the two paths written (template config and private config).
Remind the user: the private config file contains API keys and must NOT be committed to version control.
