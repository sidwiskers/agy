#!/system/bin/sh
# install_apk.sh - Installs the newly built Antigravity APK in-place via streaming session installer
LOG_FILE="/storage/emulated/0/Documents/agy/install.log"
SRC_APK="/storage/emulated/0/Documents/agy/dist/antigravity.apk"

echo "[*] Starting installation at $(date)" > "$LOG_FILE"

if [ ! -f "$SRC_APK" ]; then
    echo "[!] Error: $SRC_APK not found" >> "$LOG_FILE"
    exit 1
fi

SIZE=$(stat -c%s "$SRC_APK")
echo "[*] Package size: $SIZE bytes" >> "$LOG_FILE"

echo "[*] Creating install session..." >> "$LOG_FILE"
SESSION_OUTPUT=$(/system/bin/pm install-create -r -d -g -t)
echo "$SESSION_OUTPUT" >> "$LOG_FILE"
SESSION_ID=$(echo "$SESSION_OUTPUT" | grep -oE '[0-9]+' | head -n 1)

if [ -z "$SESSION_ID" ]; then
    echo "[!] Failed to create install session" >> "$LOG_FILE"
    exit 1
fi

echo "[*] Streaming APK to session $SESSION_ID..." >> "$LOG_FILE"
cat "$SRC_APK" | /system/bin/pm install-write -S "$SIZE" "$SESSION_ID" base - >> "$LOG_FILE" 2>&1

echo "[*] Committing install session $SESSION_ID..." >> "$LOG_FILE"
/system/bin/pm install-commit "$SESSION_ID" >> "$LOG_FILE" 2>&1
RES=$?
echo "[*] install-commit exited with code $RES" >> "$LOG_FILE"

if [ $RES -eq 0 ]; then
    echo "[*] Installation successful! Relaunching Antigravity..." >> "$LOG_FILE"
    sleep 1
    /system/bin/monkey -p com.agy -c android.intent.category.LAUNCHER 1 >> "$LOG_FILE" 2>&1
fi
