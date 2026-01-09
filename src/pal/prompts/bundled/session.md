Show or initialize the session UUID for this conversation.

## Behavior

1. **If SESSION_UUID already exists** (you generated one earlier in this conversation):
   - Output the existing SESSION_UUID

2. **If SESSION_UUID does not exist** (first time in this conversation):
   - Generate a new random UUID (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
   - Remember it as your SESSION_UUID for all future operations in this conversation
   - Output the newly generated SESSION_UUID

## Output Format

```
Session: <SESSION_UUID>
```

If newly initialized, add:
```
Session: <SESSION_UUID> (initialized)
```

## Usage

```
$$session           # Show or init session UUID
```

## Notes

- The SESSION_UUID is used by `$$tag` and `$$tags` commands to scope tagged content to this conversation
- Always use the SAME UUID throughout the entire conversation
- Output the UUID so it stays visible in the conversation context
