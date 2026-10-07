#!/bin/sh
#
# Check an agent's commit message before committing it.
#
#   <type>(<scope>): <subject> [BOT]
#
# Usage:
#   .githooks/validate-commit-msg.sh -m "fix(api): guard empty metadata [BOT]"
#   .githooks/validate-commit-msg.sh path/to/COMMIT_EDITMSG
#   printf '%s\n' "$msg" | .githooks/validate-commit-msg.sh -
#
# Exit 0 = valid, message may be committed.
# Exit 1 = invalid, with the specific reason on stderr. Do not commit.
# Exit 2 = usage error.
#
# The format itself is checked by .githooks/commit-msg, the one implementation,
# which git runs on every commit anyway. This adds only what holds for agents
# and not for people: the marker is required, and the description says enough.
# It is committed beside the hook so every clone has it; git runs only the
# hooks it has names for, so it never runs on its own.

LC_ALL=C
export LC_ALL

usage() {
    cat >&2 <<'EOF'
usage: validate-commit-msg.sh (-m <message> | <file> | -)

Required format:
    <type>(<scope>): <subject> [BOT]

    type     one of: feat fix docs refactor perf test build ci chore data
    scope    optional, lowercase letters, digits and . _ / -
    subject  imperative, lowercase first letter, no trailing full stop,
             at least 10 characters
    marker   the literal [BOT], uppercase, as the last token
    the whole subject line is at most 72 characters
EOF
    exit 2
}

fail() {
    printf 'INVALID commit message: %s\n' "$1" >&2
    exit 1
}

[ $# -ge 1 ] || usage

hook="$(cd "$(dirname "$0")" && pwd)/commit-msg"
[ -f "$hook" ] || { printf 'missing %s\n' "$hook" >&2; exit 2; }

tmp=$(mktemp) || exit 2
trap 'rm -f "$tmp"' EXIT

case "$1" in
    -m) [ $# -ge 2 ] || usage; printf '%s\n' "$2" > "$tmp" ;;
    -) cat > "$tmp" ;;
    -h|--help) usage ;;
    *) [ -f "$1" ] || { printf 'no such file: %s\n' "$1" >&2; exit 2; }
       cat "$1" > "$tmp" ;;
esac

sh "$hook" "$tmp" || exit 1

# Read the subject the way the hook does.
subject=$(sed -e '/^# -* >8 -*$/,$d' -e '/^#/d' "$tmp" | sed '/./,$!d' | head -n 1)

case "$subject" in
    *' [BOT]') ;;
    *) fail "an agent's commit ends its subject line with ' [BOT]'" ;;
esac

description=${subject#*: }
description=${description% \[BOT\]}
length=$(printf '%s' "$description" | tr -d '\200-\277' | wc -c | tr -d ' ')
[ "$length" -ge 10 ] || fail "description \"$description\" is too short to be informative"

printf 'OK: %s\n' "$subject"
exit 0
