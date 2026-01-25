---
# Specification for $$notes ai

arguments:
  -n:
    alias: --limit
    description: Number of results
    type: integer
    required: false
    default: 10
  -r:
    alias: --ratio
    description: Semantic ratio 0-1 (higher = more semantic matching)
    type: float
    required: false
    default: 0.9
  -t:
    alias: --tags
    description: Filter by tags (comma-separated)
    type: string
    required: false

# Search query is required
rest: text
rest_required: true
rest_description: The semantic search query
---

# AI Semantic Search

Search notes using AI embeddings for semantic similarity.

## Execution

Execute via the `pal_curl` tool:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","limit":<n>,"hybrid":{"semanticRatio":<ratio>,"embedder":"ollama"}}'
```

With tag filter:
```curl
curl -s -X POST 'http://meilisearch:7700/indexes/notes/search' \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","limit":<n>,"hybrid":{"semanticRatio":<ratio>,"embedder":"ollama"},"filter":"tags = \"TAG1\""}'
```

## Output Format

**AI Search for "{query}"** ({count} hits, {semanticHitCount} semantic){filter_info}

| ID | Title | Tags | Created | Preview |
|----|-------|------|---------|---------|
| `{id[:8]}` | {title} | `tag1` `tag2` | {created_at[:10]} | {content[:100]}... |

Note: Results are based on meaning, not just keywords. A search for "container networking" might find notes about "Docker bridge modes" even without those exact words.
