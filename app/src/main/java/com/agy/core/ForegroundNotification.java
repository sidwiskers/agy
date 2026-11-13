package com.agy.core;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.util.Log;

/** Builds and updates the low-importance ongoing core notification with live progress tracking. */
public final class ForegroundNotification {

    private static final String TAG = "ForegroundNotification";
    public static final int NOTIFICATION_ID = 1001;
    public static final String CHANNEL_ID = "core_channel";
    private static volatile Context sAppContext = null;

    private ForegroundNotification() {
    }

    public static void start(Service service) {
        if (service != null) {
            sAppContext = service.getApplicationContext();
        }
        ensureChannel(service);
        Notification notification = build(service, "Antigravity", "Core active", false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            service.startForeground(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            service.startForeground(NOTIFICATION_ID, notification);
        }
    }

    public static void update(Context context, String status) {
        updateProgress(context, "Antigravity", status, false);
    }

    public static void updateProgress(Context context, String title, String status, boolean isGenerating) {
        if (context == null) {
            context = sAppContext;
        }
        if (context == null) return;
        try {
            ensureChannel(context);
            NotificationManager manager =
                    (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                manager.notify(NOTIFICATION_ID, build(context, title, status, isGenerating));
            }
        } catch (Exception e) {
            Log.w(TAG, "Failed to update foreground notification", e);
        }
    }

    private static void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager =
                    (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID, "Antigravity Service", NotificationManager.IMPORTANCE_LOW);
                channel.setDescription("Background core service and task execution progress");
                channel.setShowBadge(false);
                channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
                manager.createNotificationChannel(channel);
            }
        }
    }

    private static Notification build(Context context, String title, String status, boolean isGenerating) {
        int icon = context.getResources().getIdentifier(
                "ic_notification", "drawable", context.getPackageName());
        if (icon == 0) {
            icon = android.R.drawable.stat_notify_sync;
        }

        Intent openIntent = new Intent(context, com.agy.ui.MainActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent contentPendingIntent = PendingIntent.getActivity(
                context,
                0,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(context, CHANNEL_ID)
                : new Notification.Builder(context);

        String effectiveTitle = title != null && !title.isEmpty() ? title : "Antigravity";
        String effectiveStatus = status != null && !status.isEmpty() ? status : (isGenerating ? "Generating..." : "Core active");

        builder.setContentTitle(effectiveTitle)
                .setContentText(effectiveStatus)
                .setSmallIcon(icon)
                .setContentIntent(contentPendingIntent)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setVisibility(Notification.VISIBILITY_PUBLIC)
                .setShowWhen(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            builder.setSubText(isGenerating ? "Generating" : "Ready");
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.setCategory(isGenerating ? Notification.CATEGORY_PROGRESS : Notification.CATEGORY_SERVICE);
        }

        builder.setStyle(new Notification.BigTextStyle().bigText(effectiveStatus));

        if (isGenerating) {
            builder.setProgress(0, 0, true);
        } else {
            builder.setProgress(0, 0, false);
        }

        // Add quick action to open the app
        Notification.Action openAction = new Notification.Action.Builder(
                icon,
                "Open",
                contentPendingIntent
        ).build();
        builder.addAction(openAction);

        return builder.build();
    }
}
