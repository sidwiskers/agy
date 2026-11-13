#!/usr/bin/env bash
# tools/fetch_deps.sh - Pulls prebuilt build dependencies from GitHub Releases if missing

set -euo pipefail

REPO="sidwiskers/agy"
RELEASE_TAG="v2.4.1-deps"
BASE_URL="https://github.com/${REPO}/releases/download/${RELEASE_TAG}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$ROOT_DIR/tools" "$ROOT_DIR/modules/core/pristine" "$ROOT_DIR/env/bootstrap"

download_if_missing() {
    local rel_path="$1"
    local file_name="$2"
    local full_path="$ROOT_DIR/$rel_path"

    if [[ -f "$full_path" ]]; then
        echo "[OK] Found $rel_path"
    else
        echo "[*] Downloading $rel_path..."
        curl -fSL "${BASE_URL}/${file_name}" -o "$full_path"
        echo "[OK] Downloaded $rel_path"
    fi
}

download_if_missing "tools/android.jar" "android.jar"
download_if_missing "tools/r8.jar" "r8.jar"
download_if_missing "modules/core/pristine/language_server.tar.gz" "language_server.tar.gz"
download_if_missing "env/bootstrap/bootstrap-aarch64.zip" "bootstrap-aarch64.zip"

echo "[✓] All dependencies verified."
