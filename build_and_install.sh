#!/usr/bin/env bash
# build_and_install.sh - Builds the Antigravity APK and immediately updates it on-device
# Usage:
#   bash build_and_install.sh [--region-bypass]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANDROID_DATA="${ANDROID_DATA:-/data}"

echo "[*] Building Antigravity APK..."
bash "$SCRIPT_DIR/build.sh" "$@"

TARGET_APK="$SCRIPT_DIR/dist/antigravity.apk"
if [[ " $* " == *" --region-bypass "* ]] || [[ " $* " == *" --bypass "* ]]; then
    TARGET_APK="$SCRIPT_DIR/dist/antigravity-region-bypass.apk"
fi

if [[ ! -f "$TARGET_APK" ]]; then
    TARGET_APK=$(ls -t "$SCRIPT_DIR/dist/"*.apk 2>/dev/null | head -n 1)
fi

if [[ ! -f "$TARGET_APK" ]]; then
    echo "[!] Error: No output APK found in dist/" >&2
    exit 1
fi

echo "[*] Installing $TARGET_APK onto device..."

if command -v su >/dev/null 2>&1 && su -c "id" >/dev/null 2>&1; then
    echo "[*] Installing via KernelSU root (su)..."
    su -c "pm install -r '$TARGET_APK'"
    echo "[✓] Installation complete via su."
elif command -v rish >/dev/null 2>&1 && rish -c "id" >/dev/null 2>&1; then
    echo "[*] Installing via Shizuku ADB shell (rish)..."
    rish -c "pm install -r '$TARGET_APK'"
    echo "[✓] Installation complete via rish."
else
    echo "[!] Neither su nor rish is accessible. Opening system package installer..."
    am start -a android.intent.action.VIEW -d "file://$TARGET_APK" -t "application/vnd.android.package-archive" || true
fi
