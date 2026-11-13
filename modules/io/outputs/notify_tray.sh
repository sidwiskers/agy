#!/usr/bin/env bash
# notify_tray.sh - Dispatches an Antigravity event to the Android system notification tray.
# Reads JSON event envelope from stdin.

read -r RAW_JSON || exit 0
[ -z "$RAW_JSON" ] && exit 0

EVENT_NAME=$(echo "$RAW_JSON" | grep -o '"event"[[:space:]]*:[[:space:]]*"[^"]*' | head -n 1 | cut -d'"' -f4)
MESSAGE=$(echo "$RAW_JSON" | grep -o '"message"[[:space:]]*:[[:space:]]*"[^"]*' | head -n 1 | cut -d'"' -f4)
[ -z "$MESSAGE" ] && MESSAGE=$(echo "$RAW_JSON" | grep -o '"url"[[:space:]]*:[[:space:]]*"[^"]*' | head -n 1 | cut -d'"' -f4)
[ -z "$MESSAGE" ] && MESSAGE="Event received: $EVENT_NAME"

# Check if agy-notify exists
if command -v agy-notify >/dev/null 2>&1; then
    agy-notify post -t "Antigravity: $EVENT_NAME" -m "$MESSAGE" >/dev/null 2>&1 || true
elif [ -x /system/bin/am ]; then
    /system/bin/am broadcast -a com.agy.ACTION_NOTIFY --es title "Antigravity" --es message "$MESSAGE" >/dev/null 2>&1 || true
else
    echo "[NOTIFY] $EVENT_NAME: $MESSAGE"
fi

# Trigger toast with sound and subtle haptic pulse for completions and errors
case "$EVENT_NAME" in
    *completed*|*done*)
        if command -v agy-toast >/dev/null 2>&1; then
            agy-toast "Antigravity: $MESSAGE" >/dev/null 2>&1 || true
        else
            curl -s -X POST http://127.0.0.1:45160/gateway -H "Content-Type: application/json" -d '{"command":"toast","payload":{"message":"Antigravity: '"$MESSAGE"'","sound":true}}' >/dev/null 2>&1 || true
        fi
        if command -v agy-vibrate >/dev/null 2>&1; then
            agy-vibrate success >/dev/null 2>&1 || true
        fi
        ;;
    *error*|*fail*)
        if command -v agy-vibrate >/dev/null 2>&1; then
            agy-vibrate error >/dev/null 2>&1 || true
        else
            curl -s -X POST http://127.0.0.1:45160/gateway -H "Content-Type: application/json" -d '{"command":"vibrate","payload":{"duration_ms":250}}' >/dev/null 2>&1 || true
        fi
        ;;
esac

exit 0
