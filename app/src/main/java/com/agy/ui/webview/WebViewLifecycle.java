package com.agy.ui.webview;

import android.util.Log;
import android.webkit.WebView;

/** WebView resume/timer/memory lifecycle, kept out of the activity. */
public final class WebViewLifecycle {

    private static final String TAG = "WebViewHost";

    private WebViewLifecycle() {
    }

    /** Resume the page and tell it the host is back in front. */
    public static void resume(WebView webView) {
        if (webView == null) {
            return;
        }
        try {
            webView.onResume();
            webView.resumeTimers();
            webView.evaluateJavascript(
                    "(function(){ " +
                    "  try { window.dispatchEvent(new CustomEvent('agy:host-resume')); } catch(e){} " +
                    "  try { window.dispatchEvent(new Event('resize')); } catch(e){} " +
                    "  try { window.dispatchEvent(new Event('focus')); } catch(e){} " +
                    "})();",
                    null);
        } catch (Exception e) {
            Log.w(TAG, "failed to resume webView", e);
        }
    }

    /** Called while host activity is paused; intentionally a no-op to keep UI rendering and streams alive. */
    public static void pause(WebView webView) {
        // DO NOT call webView.onPause() or webView.pauseTimers()!
        // Calling webView.onPause() tells Chromium to suspend its compositor and mark
        // WebContents as hidden, which freezes streaming chat tokens and DOM updates.
        // Leaving it active keeps the UI and token streaming alive continuously.
    }

    public static void freeMemory(WebView webView) {
        if (webView == null) {
            return;
        }
        try {
            webView.freeMemory();
        } catch (Exception e) {
            Log.w(TAG, "freeMemory failed", e);
        }
    }
}
