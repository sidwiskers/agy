package com.agy.runtime;

import android.content.Context;

import com.agy.BuildConfig;

/** App-level constants sourced from the generated BuildConfig. */
public final class RuntimeConfig {

    public static final int DEFAULT_HTTPS_PORT = BuildConfig.PORT;
    public static final String CORE_VERSION = BuildConfig.CORE_VERSION;
    public static final String APP_VERSION_NAME = BuildConfig.APP_VERSION_NAME;
    public static final int APP_VERSION_CODE = BuildConfig.APP_VERSION_CODE;
    public static final int MIN_API = BuildConfig.MIN_API;
    public static final int TARGET_SDK = BuildConfig.TARGET_SDK;
    public static final boolean DEBUG = BuildConfig.DEBUG;

    private RuntimeConfig() {
    }

    /** Returns the active core/IDE version, allowing dynamic override via ~/.gemini/config/core_version.txt */
    public static String coreVersion(Context appContext) {
        if (appContext != null) {
            try {
                java.io.File overrideFile = new java.io.File(appContext.getFilesDir(), ".gemini/config/core_version.txt");
                if (overrideFile.isFile() && overrideFile.canRead()) {
                    byte[] bytes = java.nio.file.Files.readAllBytes(overrideFile.toPath());
                    String text = new String(bytes, java.nio.charset.StandardCharsets.UTF_8).trim();
                    if (!text.isEmpty()) {
                        return text;
                    }
                }
            } catch (Exception ignored) {
            }
        }
        return CORE_VERSION;
    }

    /** The port from res/values/gen.xml, else the BuildConfig default. */
    public static int httpsPort(Context appContext) {
        if (appContext != null) {
            try {
                int resId = appContext.getResources().getIdentifier(
                        "https_server_port", "integer", appContext.getPackageName());
                if (resId != 0) {
                    return appContext.getResources().getInteger(resId);
                }
            } catch (Exception ignored) {
            }
        }
        return DEFAULT_HTTPS_PORT;
    }
}
