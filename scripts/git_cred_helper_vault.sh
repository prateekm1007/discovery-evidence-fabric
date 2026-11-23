#!/bin/sh
# git credential helper — reads the gitignored vault (.env.keys) and
# emits the GH credential for github.com pushes ONLY. The vault is
# loaded at call time (the r7_queue_runner contract); no credential is
# ever echoed to a log beyond the git credential protocol stream.
V="/home/z/my-project/repo/.env.keys"
input=$(cat)
proto=$(printf '%s\n' "$input" | sed -n 's/^protocol=//p')
host=$(printf '%s\n' "$input" | sed -n 's/^host=//p')
[ "$proto" = "https" ] || exit 0
case "$host" in
  github.com*) ;;
  *) exit 0 ;;
esac
tok=$(grep -E '^GH_PAT=' "$V" | head -1 | cut -d= -f2-)
[ -n "$tok" ] || exit 0
printf 'protocol=https\nhost=%s\nusername=x-access-token\npassword=%s\n' "$host" "$tok"
