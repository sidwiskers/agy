#!/system/bin/sh
# install_apk.sh - Installs the newly built Antigravity APK in-place via streaming session installer
LOG="/data/local/tmp/install.log"
USER_LOG="/storage/emulated/0/Documents/agy/install.log"
SRC_APK="/storage/emulated/0/Documents/agy/dist/antigravity.apk"

echo "[*] Starting installation at $(date)" > "$LOG"

if [ ! -f "$SRC_APK" ]; then
    echo "[!] Error: $SRC_APK not found" >> "$LOG"
    cp "$LOG" "$USER_LOG" 2>/dev/null
    exit 1
fi

SIZE=$(stat -c%s "$SRC_APK")
echo "[*] Package size: $SIZE bytes" >> "$LOG"

echo "[*] Creating install session..." >> "$LOG"
SESSION_OUTPUT=$(/system/bin/pm install-create -r -d -g -t)
echo "$SESSION_OUTPUT" >> "$LOG"
SESSION_ID=$(echo "$SESSION_OUTPUT" | grep -oE '[0-9]+' | head -n 1)

if [ -z "$SESSION_ID" ]; then
    echo "[!] Failed to create install session" >> "$LOG"
    cp "$LOG" "$USER_LOG" 2>/dev/null
    exit 1
fi

echo "[*] Streaming APK to session $SESSION_ID..." >> "$LOG"
cat "$SRC_APK" | /system/bin/pm install-write -S "$SIZE" "$SESSION_ID" base - >> "$LOG" 2>&1
WRITE_RES=$?
echo "[*] Stream exit: $WRITE_RES" >> "$LOG"

if [ $WRITE_RES -ne 0 ]; then
    echo "[!] Stream failed, abandoning session" >> "$LOG"
    /system/bin/pm install-abandon "$SESSION_ID" >> "$LOG" 2>&1
    cp "$LOG" "$USER_LOG" 2>/dev/null
    exit 1
fi

echo "[*] Scheduling install-commit in background..." >> "$LOG"
cp "$LOG" "$USER_LOG" 2>/dev/null

(
    sleep 2
    echo "[*] Committing install session $SESSION_ID..." >> "$LOG"
    /system/bin/pm install-commit "$SESSION_ID" >> "$LOG" 2>&1
    RES=$?
    echo "[*] install-commit exited with code $RES" >> "$LOG"
    if [ $RES -eq 0 ]; then
        echo "[*] Installation successful! Relaunching Antigravity..." >> "$LOG"
        sleep 1
        /system/bin/monkey -p com.agy -c android.intent.category.LAUNCHER 1 >> "$LOG" 2>&1
    fi
    cp "$LOG" "$USER_LOG" 2>/dev/null
) &

echo "[*] Commit scheduled. Stream complete!" >> "$LOG"
cp "$LOG" "$USER_LOG" 2>/dev/null
exit 0
