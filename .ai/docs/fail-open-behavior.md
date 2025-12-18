File: .ai/docs/fail-open-behavior.md

Purpose: Documents SafeShell's fail-open behavior and safety guarantees

Exports: Fail-open philosophy, failure modes, safety mechanisms

Depends: init.bash, safeshell-check, safeshell-shim

Overview: Explains how SafeShell handles daemon failures to ensure users never
    get locked out of their shell even when the daemon is down or broken.

# Fail-Open Behavior

**Critical Design Principle**: SafeShell must NEVER lock users out of their shell.

## Philosophy

SafeShell is designed to prevent accidents, not to create an adversarial security
boundary. Therefore, when the daemon is unavailable or malfunctioning, SafeShell
defaults to **allowing commands** rather than blocking them.

This is called "fail-open" behavior (as opposed to "fail-closed").

## Why Fail-Open?

1. **User Experience**: Users should never be locked out by a broken daemon
2. **Recovery**: Users need shell access to diagnose and fix daemon issues
3. **Trust Model**: SafeShell assumes cooperative AI agents, not adversaries
4. **Practicality**: A safety tool that breaks the shell is worse than no tool

## Failure Modes Handled

SafeShell fails open in these scenarios:

### 1. Daemon Not Running
- **Detection**: Socket file doesn't exist at `~/.safeshell/daemon.sock`
- **Behavior**: All commands allowed immediately
- **Code**: `init.bash` lines 81-83, `safeshell-check` lines 52-61

### 2. Daemon Unresponsive
- **Detection**: Connection timeout (30 seconds)
- **Behavior**: Commands execute after timeout
- **Code**: `safeshell-check` lines 91-98 (socat/nc timeout)

### 3. Socket Broken/Corrupt
- **Detection**: Connection refused or connection error
- **Behavior**: Commands allowed
- **Code**: `safeshell-check` lines 119-126

### 4. Communication Timeout
- **Detection**: No response received within timeout
- **Behavior**: Commands execute
- **Code**: `safeshell-check` lines 119-126

### 5. Unparseable Response
- **Detection**: JSON parsing fails on daemon response
- **Behavior**: Commands allowed
- **Code**: `safeshell-check` lines 168-170

### 6. safeshell-check Not Found
- **Detection**: Cannot locate safeshell-check script
- **Behavior**: Protection disabled, warning shown
- **Code**: `init.bash` lines 64-67

## Implementation Layers

### Layer 1: Shell Init (init.bash)

```bash
# Check if socket exists - fail open if not
if [[ ! -S "$socket" ]]; then
    return 0  # Daemon not running, allow command
fi
```

### Layer 2: Check Script (safeshell-check)

```bash
# If communication failed - fail open
if [[ $COMM_EXIT -ne 0 ]] || [[ -z "$RESPONSE" ]]; then
    if [[ $EXECUTE_MODE -eq 1 ]]; then
        eval "$COMMAND"
        exit $?
    else
        exit 0  # Check mode: allow
    fi
fi
```

### Layer 3: Shim Script (safeshell-shim)

```bash
# Quick check: is daemon socket present? If not, fail-open
if [[ ! -S "$SOCKET" ]]; then
    exec "$REAL_CMD" "$@"
fi
```

### Layer 4: Python Client (client.py)

```python
def evaluate_fast(..., fail_open: bool = False):
    if not sock_path.exists():
        if fail_open:
            return (True, None)  # Daemon not running
        raise ConnectionError(...)
```

## Testing Fail-Open

Use the test script to verify fail-open behavior:

```bash
bash tests/manual/test_fail_open.sh
```

This verifies:
- Commands work when daemon is down
- Shell builtins work when daemon is down  
- safeshell-check allows commands when daemon is down

## Recovery Procedure

If SafeShell has locked you out (this should never happen, but just in case):

### Emergency Recovery

1. **Remove from current shell**:
   ```bash
   unset BASH_ENV
   unset -f cd source eval
   export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v safeshell | tr '\n' ':')
   ```

2. **Disable in .bashrc**:
   - Comment out or remove the `source ~/.safeshell/init.bash` line
   - Comment out or remove the `export BASH_ENV=~/.safeshell/init.bash` line

3. **Start new shell**:
   ```bash
   bash --norc
   ```

4. **Fix or remove SafeShell**:
   ```bash
   rm -rf ~/.safeshell
   ```

## Future Improvements

Potential enhancements to fail-open behavior:

1. **Timeout Configuration**: Make timeout values configurable
2. **Degraded Mode**: Allow with warning instead of silently
3. **Health Checks**: Periodic daemon health checks
4. **Fallback Rules**: Simple shell-based rules when daemon is down

## Related Files

- `src/safeshell/shims/init.bash` - Shell initialization
- `src/safeshell/shims/safeshell-check` - Check/execute script  
- `src/safeshell/shims/safeshell-shim` - Command shim
- `src/safeshell/wrapper/client.py` - Python daemon client
- `tests/manual/test_fail_open.sh` - Fail-open tests
