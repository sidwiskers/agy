package com.agy.tile;

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
 * Native Quick Settings tile allowing users to monitor core status and
 * quickly launch Antigravity directly from the Android Quick Settings shade.
 */
public class AgyTileService extends TileService {

    private static final String TAG = "AgyTileService";

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
                CoreServiceLauncher.start(this);
            }
            Intent intent = new Intent(this, MainActivity.class);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivityAndCollapse(intent);
        } catch (Exception e) {
            Log.w(TAG, "Tile onClick failed", e);
        }
        updateTileState();
    }

    private void updateTileState() {
        Tile tile = getQsTile();
        if (tile == null) return;
        boolean isRunning = CoreRuntimeState.serverUrl != null;
        tile.setState(isRunning ? Tile.STATE_ACTIVE : Tile.STATE_INACTIVE);
        tile.setLabel("Antigravity");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            tile.setSubtitle(isRunning ? "Port " + CoreRuntimeState.httpsPort : "Stopped");
        }
        int iconRes = getResources().getIdentifier("ic_notification", "drawable", getPackageName());
        if (iconRes != 0) {
            tile.setIcon(Icon.createWithResource(this, iconRes));
        }
        tile.updateTile();
    }
}
