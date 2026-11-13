package com.agy.tile;

import android.content.ComponentName;
import android.content.Context;
import android.graphics.drawable.Icon;
import android.os.Build;
import android.service.quicksettings.Tile;
import android.service.quicksettings.TileService;
import android.util.Log;

import com.agy.core.CoreRuntimeState;
import com.agy.core.CoreServiceLauncher;

/**
 * Native Quick Settings tile allowing users to monitor core status and
 * toggle the Antigravity background core server directly from the Android Quick Settings shade.
 */
public class AgyTileService extends TileService {

    private static final String TAG = "AgyTileService";

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
            if (isRunning) {
                Log.i(TAG, "Tile tapped: stopping core server...");
                CoreServiceLauncher.stop(this);
                renderTile(false, "Stopping...");
            } else {
                Log.i(TAG, "Tile tapped: starting core server...");
                CoreServiceLauncher.start(this);
                renderTile(true, "Starting...");
            }
        } catch (Exception e) {
            Log.w(TAG, "Tile onClick failed", e);
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
        if (isRunning) {
            subtitle = "Running • :" + CoreRuntimeState.httpsPort;
        } else if (CoreRuntimeState.restarting) {
            subtitle = "Restarting...";
        } else {
            subtitle = "Stopped • Tap to start";
        }
        renderTile(isRunning, subtitle);
    }
}
