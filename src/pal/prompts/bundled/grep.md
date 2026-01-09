Search text for patterns, similar to GNU grep.

## Usage

```
$$grep [OPTIONS] PATTERN
```

Works with piped input: `$$echo $REPLIES | grep pattern`

## Options

| Flag | Long Form | Description |
|------|-----------|-------------|
| `-i` | `--ignore-case` | Case-insensitive matching |
| `-c` | `--count` | Print only a count of matching lines |
| `-v` | `--invert-match` | Select non-matching lines |
| `-A NUM` | `--after-context=NUM` | Print NUM lines after each match |
| `-B NUM` | `--before-context=NUM` | Print NUM lines before each match |

## Execution

1. **Parse arguments**: Extract flags and the PATTERN from user input
2. **Get input text**: Use the piped input (text before `| grep`)
3. **Split into lines**: Process the input line by line
4. **Apply pattern matching**:
   - If `-i`: match case-insensitively
   - If `-v`: select lines that do NOT match
   - Otherwise: select lines that match the pattern
5. **Format output**:
   - If `-c`: output only the count of matching lines
   - If `-A`/`-B`: include context lines (mark matches vs context)
   - Otherwise: output matching lines, one per line

## Output Format

- Default: matching lines, one per line
- With `-c`: single number (count of matches)
- With context (`-A`/`-B`): separate groups with `--`

## Examples

```
$$echo $REPLIES | grep error
$$echo $REPLIES | grep -i ERROR
$$echo $REPLIES | grep -c TODO
$$echo $REPLIES | grep -v debug
$$echo $REPLIES | grep -B 2 -A 2 exception
```

## Rules

- Pattern is treated as a substring match (not regex) unless it looks like a simple regex
- Empty pattern matches all lines
- If no matches found, output nothing (empty result)
- Preserve original line content exactly (no trimming)
