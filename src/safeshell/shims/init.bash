# SafeShell Shell Integration
# Source this from .bashrc: source ~/.safeshell/init.bash
#
# This provides:
# 1. PATH modification to use command shims
# 2. Function overrides for builtins (cd, source)
#
# Protection is automatically configured based on the detected environment.

# Skip if already loaded
[[ -n "$SAFESHELL_LOADED" ]] && return
export SAFESHELL_LOADED=1

# --- Context Detection ---
# Determine if we're in an AI-controlled context.
# Add vendor-specific checks here (only place for vendor detection).
__SAFESHELL_IS_AI=0
[[ "$SAFESHELL_CONTEXT" == "ai" ]] && __SAFESHELL_IS_AI=1
[[ "$WARP_AI_AGENT" == "1" ]] && __SAFESHELL_IS_AI=1
# Add other AI tool detections here:
# [[ -n "$CURSOR_AI" ]] && __SAFESHELL_IS_AI=1

# --- Tool Pattern Detection ---
# Hook-based tools (Claude Code, etc.) have pre-execution hooks that
# already validate commands - loading shims would cause double-checking.

# Pattern: Claude Code (hook-protected)
# The PreToolUse hook validates commands before execution.
# Skip shim loading to avoid double-approval issues.
if [[ -n "$CLAUDECODE" ]]; then
    return
fi

# Pattern: Other hook-protected tools can be added here:
# if [[ -n "$CURSOR_HOOK_PROTECTED" ]]; then return; fi

# Pattern: Interactive shell OR non-interactive without hook protection
# Load full shim protection below.

# Find safeshell-check (bash client - no Python!)
__safeshell_find_check() {
    # Check common locations
    local locations=(
        "$HOME/.safeshell/shims/safeshell-check"
        "$HOME/.local/bin/safeshell-check"
        "/usr/local/bin/safeshell-check"
    )

    for loc in "${locations[@]}"; do
        [[ -x "$loc" ]] && echo "$loc" && return
    done

    # Check if in PATH
    if command -v safeshell-check &>/dev/null; then
        command -v safeshell-check
        return
    fi

    return 1
}

__SAFESHELL_CHECK=$(__safeshell_find_check)

if [[ -z "$__SAFESHELL_CHECK" ]]; then
    echo "[SafeShell] Warning: safeshell-check not found. Protection disabled." >&2
    return
fi

# Helper function to check commands with daemon (check-only mode)
# Returns 0 (allow) if daemon unreachable - fail-open for shell startup
__safeshell_check() {
    local cmd="$1"

    # Bypass mode - skip evaluation (used for internal condition checks)
    if [[ "$SAFESHELL_BYPASS" == "1" ]]; then
        return 0
    fi

    # Quick check: is daemon socket present?
    local socket="${SAFESHELL_SOCKET:-$HOME/.safeshell/daemon.sock}"
    if [[ ! -S "$socket" ]]; then
        return 0  # Daemon not running, allow command
    fi

    # Use safeshell-check (pure bash, no Python startup!)
    local result
    result=$("$__SAFESHELL_CHECK" "$cmd" 2>&1)
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        builtin echo "$result" >&2
    fi

    return $exit_code
}

# --- PATH for command shims ---
__SAFESHELL_SHIM_DIR="${SAFESHELL_SHIM_DIR:-$HOME/.safeshell/shims}"
if [[ -d "$__SAFESHELL_SHIM_DIR" ]]; then
    export PATH="$__SAFESHELL_SHIM_DIR:$PATH"
fi

# --- Builtin overrides ---
# Note: Builtins use check-only mode because they must run in the current
# shell context (e.g., cd changes the shell's working directory)
#
# These overrides are configurable via ~/.safeshell/config.yaml:
#   check_cd: true      # Override cd builtin (default: true)
#   check_source: true  # Override source/. builtin (default: true)
#   check_eval: false   # Override eval builtin (default: false - causes overhead with shell hooks)

# Load shell config (written by daemon on startup)
__SAFESHELL_SHELL_CONFIG="${SAFESHELL_DIR:-$HOME/.safeshell}/shell_config"
if [[ -f "$__SAFESHELL_SHELL_CONFIG" ]]; then
    # Source the config to get SAFESHELL_CHECK_* variables
    # shellcheck source=/dev/null
    source "$__SAFESHELL_SHELL_CONFIG"
fi

# Default values if shell_config doesn't exist (daemon not started yet)
: "${SAFESHELL_CHECK_CD:=1}"
: "${SAFESHELL_CHECK_SOURCE:=1}"
: "${SAFESHELL_CHECK_EVAL:=0}"

# Override: cd (if enabled)
# Use case: Prevent AI from leaving workspace/repository
if [[ "$SAFESHELL_CHECK_CD" == "1" ]]; then
    cd() {
        local target="${1:-$HOME}"

        # Check with SafeShell (fail-open if daemon down)
        if __safeshell_check "cd $target"; then
            builtin cd "$@"
        else
            return 1
        fi
    }
fi

# Override: source (and its alias '.') (if enabled)
# Use case: Prevent sourcing sensitive scripts
if [[ "$SAFESHELL_CHECK_SOURCE" == "1" ]]; then
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
fi

# Override: eval (if enabled)
# Use case: Prevent arbitrary code execution
# Disabled by default because shell hooks (direnv, pyenv, etc.) use eval heavily
if [[ "$SAFESHELL_CHECK_EVAL" == "1" ]]; then
    eval() {
        local code="$*"

        # Check with SafeShell (fail-open if daemon down)
        if __safeshell_check "eval $code"; then
            builtin eval "$@"
        else
            return 1
        fi
    }
fi

# NOTE: echo builtin is NOT overridden.
# Reason: echo is used heavily by shell internals (prompts, hooks, etc.)
# and overriding it causes significant evaluation noise without much
# security benefit. If you need to block specific echo commands, use
# a rule with command_startswith: "echo" instead.

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
