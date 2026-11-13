package com.agy.ui.webview;

import android.content.Context;
import android.net.Uri;
import android.util.Log;
import android.webkit.WebResourceResponse;

import com.agy.util.MimeTypes;
import com.agy.util.TrustedCoreOrigin;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Serves our extracted web assets from filesDir/web for loopback requests,
 * bypassing the core for static files. Features in-memory asset pre-warming
 * and caching for near-instant warm startups.
 */
public final class LocalAssetServer {

    private static final String TAG = "LocalAssetServer";
    private static final Map<String, byte[]> ASSET_CACHE = new ConcurrentHashMap<>();
    private static final long MAX_CACHEABLE_FILE_SIZE = 15 * 1024 * 1024; // 15MB

    private static final String[] HOT_ASSETS = {
            "index.html",
            "compiled_tailwind.css",
            "jetbox.css",
            "prism_bundle.js",
            "generated/main.js",
            "generated/bridge.core.js",
            "generated/boot/custom-elements-guard.js",
            "generated/boot/theme-bootstrap.js",
            "generated/patches/web_optimizations.js",
            "generated/patches/touch_model_menu.js",
            "generated/patches/theme_sync.js",
            "generated/patches/startup_ready.js"
    };

    /** Pre-warms hot web assets into RAM on background thread. */
    public static void prewarm(final Context context) {
        if (context == null) return;
        new Thread(() -> {
            try {
                File webDir = new File(context.getFilesDir(), "web");
                if (!webDir.isDirectory()) return;

                long totalBytes = 0;
                int count = 0;
                for (String rel : HOT_ASSETS) {
                    if (ASSET_CACHE.containsKey(rel)) continue;
                    File f = new File(webDir, rel);
                    if (f.isFile() && f.canRead() && f.length() <= MAX_CACHEABLE_FILE_SIZE) {
                        byte[] data = readFileBytes(f);
                        if (data != null) {
                            ASSET_CACHE.put(rel, data);
                            totalBytes += data.length;
                            count++;
                        }
                    }
                }
                if (count > 0) {
                    Log.i(TAG, "Pre-warmed " + count + " hot assets in RAM (" + (totalBytes / 1024) + " KB)");
                }
            } catch (Exception e) {
                Log.w(TAG, "Asset pre-warming failed", e);
            }
        }, "AgyAssetPrewarmer").start();
    }

    public WebResourceResponse intercept(Context context, Uri uri, String method, int enginePort) {
        if (uri == null || !"GET".equalsIgnoreCase(method)) {
            return null;
        }
        if (!TrustedCoreOrigin.matches(uri, enginePort)) {
            return null;
        }
        String path = uri.getPath();
        if (path == null || path.isEmpty() || "/".equals(path)) {
            return null;
        }
        // Do not intercept RPC or streaming API endpoints
        if (path.startsWith("/exa.") || path.startsWith("/jetski.") || path.contains("Service")
                || path.contains("connect-websocket")) {
            return null;
        }
        String relPath = path.startsWith("/") ? path.substring(1) : path;

        // 1. Check in-memory pre-warmed cache for instant sub-millisecond response
        byte[] cached = ASSET_CACHE.get(relPath);
        if (cached != null) {
            String mime = MimeTypes.getMimeType(relPath);
            String encoding = MimeTypes.isTextMime(mime) ? "UTF-8" : null;
            Map<String, String> headers = buildHeaders(cached.length);
            return new WebResourceResponse(mime, encoding, 200, "OK", headers, new ByteArrayInputStream(cached));
        }

        File webDir = new File(context.getFilesDir(), "web");
        File target = new File(webDir, relPath);
        try {
            String canonicalWeb = webDir.getCanonicalPath();
            String canonicalTarget = target.getCanonicalPath();
            if (!canonicalTarget.startsWith(canonicalWeb + File.separator)
                    && !canonicalTarget.equals(canonicalWeb)) {
                return null;
            }
        } catch (Exception e) {
            return null;
        }

        if (target.isFile() && target.canRead()) {
            try {
                String mime = MimeTypes.getMimeType(target.getName());
                String encoding = MimeTypes.isTextMime(mime) ? "UTF-8" : null;
                long len = target.length();
                Map<String, String> headers = buildHeaders(len);

                if (len <= MAX_CACHEABLE_FILE_SIZE) {
                    byte[] data = readFileBytes(target);
                    if (data != null) {
                        ASSET_CACHE.put(relPath, data);
                        return new WebResourceResponse(mime, encoding, 200, "OK", headers, new ByteArrayInputStream(data));
                    }
                }

                InputStream bis = new BufferedInputStream(new FileInputStream(target), 64 * 1024);
                return new WebResourceResponse(mime, encoding, 200, "OK", headers, bis);
            } catch (Exception e) {
                Log.w(TAG, "intercept failed for " + path, e);
            }
        }
        return null;
    }

    private static Map<String, String> buildHeaders(long length) {
        Map<String, String> headers = new HashMap<>();
        headers.put("Access-Control-Allow-Origin", "*");
        headers.put("Cache-Control", "public, max-age=31536000, immutable");
        headers.put("Content-Length", String.valueOf(length));
        return headers;
    }

    private static byte[] readFileBytes(File file) {
        try (FileInputStream fis = new FileInputStream(file)) {
            byte[] buf = new byte[(int) file.length()];
            int off = 0;
            while (off < buf.length) {
                int read = fis.read(buf, off, buf.length - off);
                if (read < 0) break;
                off += read;
            }
            return buf;
        } catch (Exception ignored) {
            return null;
        }
    }
}
