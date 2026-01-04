#!/bin/bash
# Setup script for PAL notes feature
# Run this after: docker compose --profile notes up -d

set -e

MEILI_URL="http://localhost:7700"
OLLAMA_URL="http://localhost:11434"

echo "=== PAL Notes Setup ==="
echo ""

# Wait for Meilisearch to be ready
echo "Waiting for Meilisearch..."
until curl -s "$MEILI_URL/health" > /dev/null 2>&1; do
    sleep 1
done
echo "✓ Meilisearch is ready"

# Wait for Ollama to be ready
echo "Waiting for Ollama..."
until curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; do
    sleep 1
done
echo "✓ Ollama is ready"

# Pull the embedding model
echo ""
echo "Pulling nomic-embed-text model (this may take a few minutes)..."
curl -s "$OLLAMA_URL/api/pull" -d '{"name":"nomic-embed-text"}' | while read -r line; do
    status=$(echo "$line" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$status" ]; then
        echo "  $status"
    fi
done
echo "✓ Model pulled"

# Create the notes index
echo ""
echo "Creating notes index..."
curl -s -X POST "$MEILI_URL/indexes" \
    -H 'Content-Type: application/json' \
    -d '{"uid": "notes", "primaryKey": "id"}' > /dev/null
echo "✓ Index created"

# Enable vector store experimental feature
echo "Enabling vector store feature..."
curl -s -X PATCH "$MEILI_URL/experimental-features" \
    -H 'Content-Type: application/json' \
    -d '{"vectorStore": true}' > /dev/null
echo "✓ Vector store enabled"

# Configure searchable attributes
echo "Configuring searchable attributes..."
curl -s -X PATCH "$MEILI_URL/indexes/notes/settings" \
    -H 'Content-Type: application/json' \
    -d '{
        "searchableAttributes": ["id", "content", "title", "tags"],
        "sortableAttributes": ["created_at"],
        "filterableAttributes": ["tags", "created_at"]
    }' > /dev/null
echo "✓ Searchable attributes configured"

# Configure embeddings for AI search (using REST source for Ollama compatibility)
echo "Configuring embeddings (hybrid search)..."
curl -s -X PATCH "$MEILI_URL/indexes/notes/settings" \
    -H 'Content-Type: application/json' \
    -d '{
        "embedders": {
            "ollama": {
                "source": "rest",
                "url": "http://ollama:11434/api/embed",
                "request": {"model": "nomic-embed-text", "input": "{{text}}"},
                "response": {"embeddings": ["{{embedding}}"]}
            }
        }
    }' > /dev/null
echo "✓ Embeddings configured"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "You can now use the notes commands:"
echo "  \$\$notes add <content>           - Add a note"
echo "  \$\$notes add -t tag1,tag2 <text> - Add with tags"
echo "  \$\$notes list                    - List recent notes"
echo "  \$\$notes search \"query\"          - Text search"
echo "  \$\$notes ai \"query\"              - AI semantic search"
echo ""
echo "Web UI available at: http://localhost:24900"
