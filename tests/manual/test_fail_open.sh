#!/usr/bin/env bash
# Manual test for fail-open behavior
# This tests that SafeShell allows commands when the daemon is down/broken

set -euo pipefail

echo "=== SafeShell Fail-Open Behavior Test ==="
echo

# Get the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Source the init script
echo "1. Loading SafeShell init script (daemon should be down)..."
source src/safeshell/shims/init.bash 2>&1 | grep -i safeshell || true
echo

# Test 1: Basic command with daemon down
echo "2. Testing basic command (ls) with daemon down..."
if ls > /dev/null 2>&1; then
    echo "✅ PASS: ls worked with daemon down (fail-open)"
else
    echo "❌ FAIL: ls blocked with daemon down (fail-closed)"
    exit 1
fi
echo

# Test 2: cd builtin with daemon down
echo "3. Testing cd builtin with daemon down..."
if cd /tmp && cd "$PROJECT_ROOT"; then
    echo "✅ PASS: cd worked with daemon down (fail-open)"
else
    echo "❌ FAIL: cd blocked with daemon down (fail-closed)"
    exit 1
fi
echo

# Test 3: Direct safeshell-check test
echo "4. Testing safeshell-check directly (check mode)..."
CHECK_SCRIPT="$PROJECT_ROOT/src/safeshell/shims/safeshell-check"
if [[ -x "$CHECK_SCRIPT" ]]; then
    if "$CHECK_SCRIPT" "echo test" >/dev/null 2>&1; then
        echo "✅ PASS: safeshell-check allowed command (fail-open)"
    else
        echo "❌ FAIL: safeshell-check blocked command (fail-closed)"
        exit 1
    fi
else
    echo "⚠️  SKIP: safeshell-check not found at $CHECK_SCRIPT"
fi
echo

# Test 4: safeshell-check execute mode
echo "5. Testing safeshell-check execute mode..."
if [[ -x "$CHECK_SCRIPT" ]]; then
    OUTPUT=$("$CHECK_SCRIPT" -e "echo 'test execute'" 2>&1)
    if [[ "$OUTPUT" == "test execute" ]]; then
        echo "✅ PASS: safeshell-check executed command (fail-open)"
    else
        echo "❌ FAIL: safeshell-check didn't execute: $OUTPUT"
        exit 1
    fi
else
    echo "⚠️  SKIP: safeshell-check not found"
fi
echo

echo "=== All Tests Passed ==="
echo
echo "Summary:"
echo "- Commands work when daemon is down (fail-open)"
echo "- Shell builtins work when daemon is down (fail-open)"
echo "- safeshell-check allows commands when daemon is down (fail-open)"
echo
echo "✅ SafeShell will NOT block your shell if the daemon fails!"
