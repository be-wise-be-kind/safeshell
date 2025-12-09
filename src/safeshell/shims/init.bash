# SafeShell Shell Integration
# Source this from .bashrc: source ~/.safeshell/init.bash
#
# This provides:
# 1. PATH modification to use command shims
# 2. Function overrides for builtins (cd, source, eval, echo)
#
# Protection is automatically configured based on the detected environment.

# Skip if already loaded
[[ -n "$SAFESHELL_LOADED" ]] && return
export SAFESHELL_LOADED=1

# --- Tool Pattern Detection ---
# Different AI tools need different protection strategies.
# Hook-based tools (Claude Code, etc.) have pre-execution hooks that
# already validate commands - loading shims would cause double-checking.

# Pattern: Claude Code (hook-protected)
# The PreToolUse hook validates commands before execution.
# Skip shim loading to avoid double-approval issues.
if [[ -n "$CLAUDECODE" ]]; then
    return
fi

# Pattern: Other hook-protected tools can be added here:
# if [[ -n "$CURSOR_SOMETHING" ]]; then return; fi

# Pattern: Interactive shell OR non-interactive without hook protection
# Load full shim protection below.

# Find safeshell-wrapper
__safeshell_find_wrapper() {
    if command -v safeshell-wrapper &>/dev/null; then
        command -v safeshell-wrapper
        return
    fi

    local locations=(
        "$HOME/.local/bin/safeshell-wrapper"
        "/usr/local/bin/safeshell-wrapper"
    )

    for loc in "${locations[@]}"; do
        [[ -x "$loc" ]] && echo "$loc" && return
    done

    return 1
}

__SAFESHELL_WRAPPER=$(__safeshell_find_wrapper)

if [[ -z "$__SAFESHELL_WRAPPER" ]]; then
    echo "[SafeShell] Warning: safeshell-wrapper not found. Protection disabled." >&2
    return
fi

# Helper function to check commands with daemon
# Returns 0 (allow) if daemon unreachable - fail-open for shell startup
__safeshell_check() {
    local cmd="$1"

    # Quick check: is daemon socket present?
    local socket="${SAFESHELL_SOCKET:-$HOME/.safeshell/daemon.sock}"
    if [[ ! -S "$socket" ]]; then
        return 0  # Daemon not running, allow command
    fi

    local result
    result=$(SAFESHELL_CHECK_ONLY=1 "$__SAFESHELL_WRAPPER" -c "$cmd" 2>&1)
    local exit_code=$?

    # If check failed due to daemon issues, allow (fail-open)
    if [[ $exit_code -ne 0 && "$result" == *"Daemon unreachable"* ]]; then
        return 0
    fi

    if [[ $exit_code -ne 0 ]]; then
        echo "$result" >&2
    fi

    return $exit_code
}

# --- PATH for command shims ---
__SAFESHELL_SHIM_DIR="${SAFESHELL_SHIM_DIR:-$HOME/.safeshell/shims}"
if [[ -d "$__SAFESHELL_SHIM_DIR" ]]; then
    export PATH="$__SAFESHELL_SHIM_DIR:$PATH"
fi

# --- Builtin overrides ---

# Override: cd
# Use case: Prevent AI from leaving workspace/repository
cd() {
    local target="${1:-$HOME}"

    # Check with SafeShell (fail-open if daemon down)
    if __safeshell_check "cd $target"; then
        builtin cd "$@"
    else
        return 1
    fi
}

# Override: source (and its alias '.')
# Use case: Prevent sourcing sensitive scripts
source() {
    local script="$1"
    shift

    # Check with SafeShell (fail-open if daemon down)
    if __safeshell_check "source $script"; then
        builtin source "$script" "$@"
    else
        return 1
    fi
}

# '.' is an alias for source
.() {
    source "$@"
}

# Override: eval
# Use case: Prevent arbitrary code execution
eval() {
    local code="$*"

    # Check with SafeShell (fail-open if daemon down)
    if __safeshell_check "eval $code"; then
        builtin eval "$@"
    else
        return 1
    fi
}

# Override: echo
# Use case: Prevent echoing sensitive data or test blocking
echo() {
    # Check with SafeShell (fail-open if daemon down)
    if __safeshell_check "echo $*"; then
        builtin echo "$@"
    else
        return 1
    fi
}

# --- Restore tab completion for overridden builtins ---
# When we override builtins with functions, bash loses default completion
complete -d cd           # cd completes directories
complete -f source       # source completes files
complete -f .            # . completes files

# Only show message for interactive shells
if [[ $- == *i* ]]; then
    if [[ -S "${SAFESHELL_SOCKET:-$HOME/.safeshell/daemon.sock}" ]]; then
        builtin echo "[SafeShell] Protection active. Commands and builtins are monitored."
    else
        builtin echo "[SafeShell] Loaded (daemon not running - fail-open mode)."
    fi
fi
