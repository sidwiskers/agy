package com.agy.tile;

import android.app.PendingIntent;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.drawable.Icon;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.util.Log;

import com.agy.core.CoreRuntimeState;
import com.agy.core.CoreServiceLauncher;
import com.agy.ui.MainActivity;

/**
 * Native Quick Settings tile allowing users to monitor live agent activity
 * and quickly jump directly into Antigravity from the Quick Settings shade.
 */
public class AgyTileService extends TileService {

    private static final String TAG = "AgyTileService";
    private static volatile String sLatestStatus = null;
    private static volatile boolean sIsGenerating = false;

    public static void requestUpdate(Context context) {
        if (context != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            try {
                TileService.requestListeningState(
                        context.getApplicationContext(),
                        new ComponentName(context.getApplicationContext(), AgyTileService.class)
                );
            } catch (Exception ignored) {
            }
        }
    }

    public static void updateAgentProgress(Context context, String status, boolean isGenerating) {
        sLatestStatus = status;
        sIsGenerating = isGenerating;
        requestUpdate(context);
    }

    @Override
    public void onStartListening() {
        super.onStartListening();
        updateTileState();
    }

    @Override
    public void onClick() {
        super.onClick();
        try {
            boolean isRunning = CoreRuntimeState.serverUrl != null;
            if (!isRunning) {
                Log.i(TAG, "Tile tapped: starting core server...");
                CoreServiceLauncher.start(this);
            }

            Intent intent = new Intent(this, MainActivity.class);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);

            if (Build.VERSION.SDK_INT >= 34) {
                try {
                    PendingIntent pi = PendingIntent.getActivity(
                            this,
                            0,
                            intent,
                            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                    );
                    java.lang.reflect.Method m = TileService.class.getMethod("startActivityAndCollapse", PendingIntent.class);
                    m.invoke(this, pi);
                    return;
                } catch (Throwable ignored) {
                }
            }

            try {
                startActivityAndCollapse(intent);
            } catch (Throwable t) {
                startActivity(intent);
            }
        } catch (Exception e) {
            Log.w(TAG, "Tile onClick failed", e);
        } finally {
            updateTileState();
        }
    }

    private void renderTile(boolean active, String subtitle) {
        Tile tile = getQsTile();
        if (tile == null) return;
        tile.setState(active ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
        tile.setLabel("Antigravity");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.setSubtitle(subtitle);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            tile.setStateDescription(subtitle);
        }
        int iconRes = getResources().getIdentifier("ic_notification", "drawable", getPackageName());
        if (iconRes != 0) {
            tile.setIcon(Icon.createWithResource(this, iconRes));
        }
        tile.updateTile();
    }

    private void updateTileState() {
        boolean isRunning = CoreRuntimeState.serverUrl != null;
        String subtitle;
        if (!isRunning) {
            if (CoreRuntimeState.restarting) {
                subtitle = "Restarting...";
            } else {
                subtitle = "Stopped • Tap to start";
            }
            renderTile(false, subtitle);
        } else {
            if (sIsGenerating && sLatestStatus != null && !sLatestStatus.isEmpty()) {
                subtitle = sLatestStatus;
            } else {
                subtitle = "Ready • Tap to open";
            }
            renderTile(true, subtitle);
        }
    }
}
