Execute HTTP requests via the `curl` MCP tool.

## MCP Tool
Call `curl` with parameters:
- `command` (required): Full curl command string
- `timeout` (optional): Timeout in seconds (default 30)

## Usage
The curl tool executes curl commands on the server. Use it when instructions specify:

```
Execute via the `curl` tool:
```curl
curl -s 'http://meilisearch:7700/health'
```
```

For native execution, instructions will specify:

```
Execute directly via Bash:
```bash
curl -s 'http://meilisearch:7700/health'
```
```

## Response Format
```json
{
  "success": true,
  "output": "response body"
}
```

On error:
```json
{
  "success": false,
  "output": "",
  "error": "error message"
}
```

## Supported Flags
All standard curl flags are supported: -s, -X, -H, -d, --data-raw, etc.
