package com.agy.core;

import android.util.Log;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Protects Chromium WebView renderer processes (sandboxed_process) from being frozen
 * or killed by Android's CachedAppOptimizer when the host activity is backgrounded.
 *
 * Android 12+ app freezer (freezer_cutoff_adj = 900) automatically freezes isolated
 * renderer processes with oom_adj >= 900 after 10s in background. Setting their
 * oom_score_adj to -900 and clearing cgroup.freeze ensures uninterrupted streaming,
 * token processing, and background DOM/event loop execution.
 */
public final class SandboxedProcessProtector {

    private static final String TAG = "WebViewProtector";
    private static final AtomicBoolean running = new AtomicBoolean(false);
    private static Thread workerThread;

    private SandboxedProcessProtector() {
    }

    public static void start() {
        if (running.compareAndSet(false, true)) {
            workerThread = new Thread(SandboxedProcessProtector::loop, "AgyWebViewProtector");
            workerThread.setDaemon(true);
            workerThread.start();
            Log.i(TAG, "Started SandboxedProcessProtector daemon");
        }
    }

    public static void stop() {
        running.set(false);
        if (workerThread != null) {
            workerThread.interrupt();
            workerThread = null;
        }
    }

    /** Triggered immediately when host activity enters background or foreground. */
    public static void protectNow() {
        new Thread(SandboxedProcessProtector::runProtectionOnce, "AgyProtectNow").start();
    }

    private static void loop() {
        while (running.get()) {
            try {
                runProtectionOnce();
                Thread.sleep(4000);
            } catch (InterruptedException e) {
                break;
            } catch (Throwable t) {
                Log.w(TAG, "Protection cycle warning: " + t.getMessage());
            }
        }
    }

    public static void runProtectionOnce() {
        try {
            // Find all sandboxed_process PIDs and ensure oom_score_adj is -900 and cgroup.freeze is 0
            String script =
                "for p in $(pgrep -f sandboxed_process); do " +
                "  cur=$(cat /proc/$p/oom_score_adj 2>/dev/null); " +
                "  if [ \"$cur\" != \"-900\" ]; then " +
                "    echo -900 > /proc/$p/oom_score_adj 2>/dev/null; " +
                "  fi; " +
                "  echo 0 > /sys/fs/cgroup/apps/uid_*/pid_$p/cgroup.freeze 2>/dev/null; " +
                "  echo 0 > /sys/fs/cgroup/apps/uid_*/cgroup.freeze 2>/dev/null; " +
                "done";

            Process proc = new ProcessBuilder("su", "-c", script).start();
            proc.waitFor();
        } catch (Throwable ignored) {
        }
    }
}
