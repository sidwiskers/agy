package com.agy.runtime;

import android.content.Context;
import android.util.Log;

import com.agy.util.AtomicFileWriter;

import java.io.File;
import java.io.InputStream;

/**
 * Materializes a fully-onboarded state before the core starts, so the Welcome
 * wizard is skipped. Idempotent and non-destructive: only writes when the
 * target is absent (or a zero-byte stub).
 */
public final class OnboardingSeeder {

    private static final String TAG = "OnboardingSeeder";

    private OnboardingSeeder() {
    }

    public static void seed(Context appContext, File appData, File projects) {
        try {
            if (!appData.exists() && !appData.mkdirs()) {
                Log.w(TAG, "cannot create " + appData);
                return;
            }
            seedStateFile(appContext, "jetski_state.pbtxt", new File(appData, "jetski_state.pbtxt"));
            seedStateFile(appContext, "antigravity_state.pbtxt",
                    new File(appData, "antigravity_state.pbtxt"));

            // Seed default agent rules (AGENTS.md) into ~/.gemini/config/AGENTS.md
            File configDir = projects.getParentFile();
            if (configDir != null && (configDir.isDirectory() || configDir.mkdirs())) {
                seedStateFile(appContext, "AGENTS.md", new File(configDir, "AGENTS.md"));
                // Seed default skills into ~/.gemini/config/skills/
                seedAssetTree(appContext, RuntimePaths.SEED_ASSET + "/skills", new File(configDir, "skills"));
            }

            // The project store resolves its projects here; without the
            // pseudo-project file it logs project_store_get_file_missing.
            if (!projects.exists() && !projects.mkdirs()) {
                Log.w(TAG, "cannot create " + projects);
                return;
            }
            File outside = new File(projects, "outside-of-project.json");
            if (!outside.isFile()) {
                AtomicFileWriter.writeText(outside, "{}\n");
            }
        } catch (Exception e) {
            Log.w(TAG, "onboarding seed failed (continuing): " + e.getMessage());
        }
    }

    private static void seedStateFile(Context appContext, String assetName, File target)
            throws Exception {
        if (target.isFile() && target.length() > 0) {
            Log.i(TAG, "state present; left untouched: " + target);
            return;
        }
        try (InputStream in = appContext.getAssets().open(
                RuntimePaths.SEED_ASSET + "/" + assetName)) {
            String content = com.agy.util.IoUtil.readAll(in, "UTF-8");
            AtomicFileWriter.writeText(target, content);
        }
        Log.i(TAG, "seeded onboarding state (was missing): " + target);
    }

    private static void seedAssetTree(Context appContext, String assetDir, File targetDir) {
        try {
            String[] list = appContext.getAssets().list(assetDir);
            if (list == null || list.length == 0) return;
            if (!targetDir.exists()) targetDir.mkdirs();
            for (String file : list) {
                String subAsset = assetDir + "/" + file;
                File subTarget = new File(targetDir, file);
                String[] subList = appContext.getAssets().list(subAsset);
                if (subList != null && subList.length > 0) {
                    seedAssetTree(appContext, subAsset, subTarget);
                } else {
                    if (!subTarget.isFile() || subTarget.length() == 0) {
                        try (InputStream in = appContext.getAssets().open(subAsset)) {
                            byte[] buffer = new byte[8192];
                            int read;
                            File tmp = new File(subTarget.getAbsolutePath() + ".tmp");
                            try (java.io.FileOutputStream out = new java.io.FileOutputStream(tmp)) {
                                while ((read = in.read(buffer)) != -1) {
                                    out.write(buffer, 0, read);
                                }
                            }
                            tmp.renameTo(subTarget);
                            if (file.endsWith(".py") || file.endsWith(".sh")) {
                                subTarget.setExecutable(true, false);
                            }
                            Log.i(TAG, "seeded skill asset: " + subTarget);
                        }
                    }
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "failed seeding asset tree " + assetDir + ": " + e.getMessage());
        }
    }
}
