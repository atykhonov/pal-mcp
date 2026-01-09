Extract fenced blocks from markdown text.

## Usage

```
$$block [OPTIONS]
$$echo $REPLY | block [OPTIONS]
```

If no piped input, defaults to `$REPLY` (your last response).

## Options

| Flag | Long Form | Description |
|------|-----------|-------------|
| `-n NUM` | `--nth NUM` | Select Nth block (1-based) |
| | `--first` | First block (same as `-n1`) |
| `-l` | `--last` | Last block |
| `--lang LANG` | | Filter by language tag (e.g., `py`, `js`, `bash`) |
| `-r` | `--raw` | Output without fence markers |

Note: `-n NUM` can also be written as `-nNUM` (e.g., `-n2`, `-n3`).

## Execution

1. **Get input text**: Use piped input, or `$REPLY` if none provided
2. **Extract fenced blocks**: Find all fenced blocks (``` ... ```)
3. **Apply language filter**: If `--lang` specified, keep only matching blocks
4. **Select blocks**:
   - If `--first` or `-n1`: return first block
   - If `-l`/`--last`: return last block
   - If `-n NUM`: return Nth block
   - Otherwise: return all blocks
5. **Format output**:
   - Default: preserve fence markers and language tag
   - If `-r`/`--raw`: output content only (no fences)

## Output Format

- Default: fenced blocks with original language tags
- With `-r`: raw content without fence markers
- Multiple blocks separated by blank line
- If no blocks found, output nothing

## Examples

```
$$block                       # all blocks from last reply
$$block --first               # first block from last reply
$$block -l                    # last block from last reply
$$block -n2                   # second block
$$block -n 3                  # third block
$$block --lang python         # only python blocks
$$block --lang py --first     # first python block
$$block -r                    # all blocks, raw output
$$block --first -r            # first block, raw output
$$echo $REPLY1 | block        # all blocks from reply 1 back
$$echo $REPLY | block -r | grep async   # search within block content
```

## Language Matching

Match language tag flexibly:
- `py` matches `python`, `py`, `python3`
- `js` matches `javascript`, `js`
- `ts` matches `typescript`, `ts`
- `sh` matches `bash`, `sh`, `shell`, `zsh`
- Others: exact or prefix match

## Rules

- Preserve original indentation within blocks
- If requested block doesn't exist, output nothing
- Blocks without language tags are included unless `--lang` is specified
