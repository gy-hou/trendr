# Shared Agent Contract

## Forbidden
- 编造事实：论文 ID、引用、字段值、指标数据。
- 未经用户同意执行 destructive shell 操作（`rm -rf`、`DROP TABLE` 等）。
- 产出文件不落盘就结束（必须写完文件才能返回）。
- 在 `claude-code` runtime 使用 OpenClaw 原语（`web_fetch:`、`exec:`、`sessions_spawn`）。

## Heartbeat

文件：`<project_dir>/heartbeat.json`，每 ≤5 分钟或每完成一个子步骤写一次：

```json
{
  "agent": "<agent_id>",
  "state": "<SM state or step name>",
  "message": "<what I just did>",
  "updated_at": "<ISO 8601>"
}
```

使用原子写（先写 `.tmp`，再 rename）：
```
Write(file_path="[project_dir]/heartbeat.json.tmp", content=...)
Bash(command="mv [project_dir]/heartbeat.json.tmp [project_dir]/heartbeat.json")
```

## File I/O

- 写文件前确保父目录存在：`Bash(command="mkdir -p [dir]")`
- 原子写：先写 `<path>.tmp`，再 rename 到目标路径（避免读取半写文件）。
- 不覆盖用户手动编辑的文件：若 mtime 超过本 run 开始时间，写到 `<path>.new` 并输出提示。

