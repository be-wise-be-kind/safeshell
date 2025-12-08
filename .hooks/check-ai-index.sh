#!/bin/bash
# ==============================================================================
# File: .hooks/check-ai-index.sh
#
# Purpose: Pre-push hook to verify .ai/ file changes include index.yaml update
#
# Usage: Called automatically by git pre-push hook via .pre-commit-config.yaml
#
# Exit codes:
#   0 - Success (no .ai/ changes, or index.yaml was updated)
#   1 - Failure (.ai/ files changed without updating index.yaml)
# ==============================================================================

# Get files changed in commits being pushed (compare to upstream or last commit)
CHANGED_FILES=$(git diff --name-status @{upstream}..HEAD 2>/dev/null || git diff --name-status HEAD~1..HEAD)

# Check for .ai/ additions, deletions, or renames (A=added, D=deleted, R=renamed)
AI_CHANGES=$(echo "$CHANGED_FILES" | grep -E "^[ADR].*\.ai/")

if [ -n "$AI_CHANGES" ]; then
    # Verify index.yaml is also modified (A=added or M=modified)
    INDEX_MODIFIED=$(echo "$CHANGED_FILES" | grep -E "^[AM].*\.ai/index\.yaml$")

    if [ -z "$INDEX_MODIFIED" ]; then
        echo ""
        echo "ERROR: .ai/ files were added, deleted, or renamed without updating .ai/index.yaml"
        echo ""
        echo "Changed .ai/ files:"
        echo "$AI_CHANGES" | sed 's/^/  /'
        echo ""
        echo "Please update .ai/index.yaml to reflect these changes, then commit and push again."
        echo ""
        exit 1
    fi
fi

exit 0
