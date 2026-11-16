package com.agy.core;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.AudioAttributes;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.Log;

/**
 * Native heads-up floating notification manager.
 * Sends high-priority floating notifications that drop down over the screen on task completion.
 */
public final class FloatingNotification {

    private static final String TAG = "FloatingNotification";
    public static final String CHANNEL_ID = "antigravity_floating_alerts_v1";
    public static final String NOTIFICATION_TAG = "agy_floating_alert";

    private static volatile long sLastNotifyTime = 0;
    private static volatile String sLastNotifyMessage = "";

    private FloatingNotification() {
    }

    public static void show(Context context, String title, String message, boolean playSound) {
        show(context, title, message, playSound, null);
    }

    public static void show(Context context, String title, String message, boolean playSound, String cascadeId) {
        if (context == null) return;

        final Context appContext = context.getApplicationContext();
        final String effectiveTitle = (title != null && !title.trim().isEmpty()) ? title.trim() : "Antigravity";
        final String effectiveMessage = (message != null && !message.trim().isEmpty()) ? message.trim() : "Task completed";

        // Debounce identical notifications within 1.5 seconds
        long now = System.currentTimeMillis();
        if (now - sLastNotifyTime < 1500 && effectiveMessage.equals(sLastNotifyMessage)) {
            Log.d(TAG, "Suppressed duplicate floating notification within debounce window");
            return;
        }
        sLastNotifyTime = now;
        sLastNotifyMessage = effectiveMessage;

        try {
            ensureChannel(appContext);
            NotificationManager manager =
                    (NotificationManager) appContext.getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager == null) return;

            // Small notification icon
            int icon = appContext.getResources().getIdentifier(
                    "ic_notification", "drawable", appContext.getPackageName());
            if (icon == 0) {
                icon = android.R.drawable.stat_notify_chat;
            }

            // Optional large brand logo
            Bitmap largeIcon = null;
            int logoRes = appContext.getResources().getIdentifier(
                    "ic_launcher_logo", "drawable", appContext.getPackageName());
            if (logoRes == 0) {
                logoRes = appContext.getResources().getIdentifier(
                        "ic_launcher", "mipmap", appContext.getPackageName());
            }
            if (logoRes != 0) {
                try {
                    largeIcon = BitmapFactory.decodeResource(appContext.getResources(), logoRes);
                } catch (Throwable ignored) {}
            }

            // Click Intent to bring MainActivity forward
            Intent openIntent = new Intent(appContext, com.agy.ui.MainActivity.class);
            openIntent.setAction("com.agy.action.NOTIFICATION_CLICK");
            openIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            if (cascadeId != null && !cascadeId.isEmpty()) {
                openIntent.putExtra("cascade_id", cascadeId);
            }

            int reqCode = (int) (now % 100000);
            PendingIntent pendingIntent = PendingIntent.getActivity(
                    appContext,
                    reqCode,
                    openIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));

            Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                    ? new Notification.Builder(appContext, CHANNEL_ID)
                    : new Notification.Builder(appContext);

            builder.setContentTitle(effectiveTitle)
                    .setContentText(effectiveMessage)
                    .setSmallIcon(icon)
                    .setContentIntent(pendingIntent)
                    .setAutoCancel(true)
                    .setOngoing(false)
                    .setPriority(Notification.PRIORITY_MAX)
                    .setDefaults(Notification.DEFAULT_ALL)
                    .setVibrate(new long[]{0, 250, 100, 250})
                    .setVisibility(Notification.VISIBILITY_PUBLIC)
                    .setStyle(new Notification.BigTextStyle().bigText(effectiveMessage))
                    .setWhen(now)
                    .setShowWhen(true);

            if (largeIcon != null) {
                builder.setLargeIcon(largeIcon);
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                builder.setCategory(Notification.CATEGORY_STATUS);
            }

            // Action button inside notification card
            Notification.Action openAction = new Notification.Action.Builder(
                    icon,
                    "Open",
                    pendingIntent
            ).build();
            builder.addAction(openAction);

            // Wake screen if currently turned off so user sees the heads-up banner
            try {
                PowerManager pm = (PowerManager) appContext.getSystemService(Context.POWER_SERVICE);
                if (pm != null && !pm.isInteractive()) {
                    PowerManager.WakeLock wl = pm.newWakeLock(
                            PowerManager.SCREEN_BRIGHT_WAKE_LOCK
                                    | PowerManager.ACQUIRE_CAUSES_WAKEUP
                                    | PowerManager.ON_AFTER_RELEASE,
                            "agy:floating_notification_wake");
                    wl.acquire(3000);
                }
            } catch (Throwable ignored) {}

            // Haptic feedback
            try {
                Vibrator vibrator = (Vibrator) appContext.getSystemService(Context.VIBRATOR_SERVICE);
                if (vibrator != null && vibrator.hasVibrator()) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        vibrator.vibrate(VibrationEffect.createWaveform(new long[]{0, 180, 80, 180}, -1));
                    } else {
                        vibrator.vibrate(new long[]{0, 180, 80, 180}, -1);
                    }
                }
            } catch (Throwable ignored) {}

            // Audio chime if requested
            if (playSound) {
                try {
                    Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
                    Ringtone r = RingtoneManager.getRingtone(appContext, soundUri);
                    if (r != null) {
                        r.play();
                    }
                } catch (Throwable ignored) {}
            }

            int notifId = (int) (now % 10000) + 2000;
            manager.notify(NOTIFICATION_TAG, notifId, builder.build());
            Log.i(TAG, "Native floating notification posted: " + effectiveTitle + " - " + effectiveMessage);
        } catch (Throwable t) {
            Log.w(TAG, "Failed to post floating notification: " + t.getMessage(), t);
        }
    }

    private static void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager =
                    (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID, "Task Completions", NotificationManager.IMPORTANCE_HIGH);
                channel.setDescription("Floating heads-up notifications when AI agent completes tasks");
                channel.enableVibration(true);
                channel.setVibrationPattern(new long[]{0, 250, 100, 250});
                channel.enableLights(true);
                channel.setLightColor(0xFF6750A4);
                channel.setShowBadge(true);
                channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);

                try {
                    Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
                    if (soundUri != null) {
                        AudioAttributes audioAttributes = new AudioAttributes.Builder()
                                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                                .setUsage(AudioAttributes.USAGE_NOTIFICATION_COMMUNICATION_INSTANT)
                                .build();
                        channel.setSound(soundUri, audioAttributes);
                    }
                } catch (Throwable ignored) {}

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    channel.setAllowBubbles(true);
                }

                manager.createNotificationChannel(channel);
            }
        }
    }
}
