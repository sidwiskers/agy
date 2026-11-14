#!/usr/bin/env python3
"""
scaffold_app.py - Instant project generator for Gradle-free Android apps.
Supports:
  Option 1: Modern Web / Hybrid Dashboard (WebView + Bridge + AMOLED Chart.js)
  Option 2: Pure Native Android (Java + XML Layouts + Custom Canvas Graph)

Usage:
    python3 scaffold_app.py --option 1 --out my-hybrid-app --pkg com.example.hybrid --name "Hybrid App"
    python3 scaffold_app.py --option 2 --out my-native-app --pkg com.example.native --name "Native App"
"""
import os
import argparse

BUILD_SH_TEMPLATE = """#!/usr/bin/env bash
# Fast Gradle-Free Direct Android Builder
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PROJECT_ROOT="$SCRIPT_DIR"
export BUILD_DIR="$PROJECT_ROOT/build"
export DIST_DIR="$PROJECT_ROOT/dist"
export APP_DIR="$PROJECT_ROOT/app"

ANDROID_JAR="${ANDROID_JAR:-/storage/emulated/0/Documents/agy/tools/android.jar}"
R8_JAR="${R8_JAR:-/storage/emulated/0/Documents/agy/tools/r8.jar}"
KEYSTORE="${KEYSTORE:-$PROJECT_ROOT/debug.keystore}"

if [ ! -f "$ANDROID_JAR" ]; then
    echo "[ERROR] Missing android.jar at $ANDROID_JAR" >&2
    exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/gen" "$BUILD_DIR/obj" "$BUILD_DIR/dex" "$BUILD_DIR/res" "$DIST_DIR"

# 1. Keystore check
if [ ! -f "$KEYSTORE" ]; then
    echo "[*] Creating debug keystore..."
    keytool -genkeypair -v -keystore "$KEYSTORE" -alias androiddebugkey \\
        -keyalg RSA -keysize 2048 -validity 10000 \\
        -storepass android -keypass android \\
        -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
fi

# 2. AAPT Generate R.java
echo "[*] [1/5] Compiling resources with AAPT..."
aapt package -f -m \\
    -J "$BUILD_DIR/gen" \\
    -M "$APP_DIR/src/main/AndroidManifest.xml" \\
    -S "$APP_DIR/src/main/res" \\
    -I "$ANDROID_JAR"

# 3. Javac
echo "[*] [2/5] Compiling Java classes..."
find "$APP_DIR/src/main/java" "$BUILD_DIR/gen" -name "*.java" > "$BUILD_DIR/sources.txt"
javac -encoding UTF-8 -source 1.8 -target 1.8 \\
    -d "$BUILD_DIR/obj" \\
    -cp "$ANDROID_JAR" \\
    "@$BUILD_DIR/sources.txt"

# 4. D8 Dexer
echo "[*] [3/5] Dexing bytecode with D8..."
if [ -f "$R8_JAR" ]; then
    java -cp "$R8_JAR" com.android.tools.r8.D8 --release --min-api 24 \\
        --lib "$ANDROID_JAR" \\
        --output "$BUILD_DIR/dex" \\
        $(find "$BUILD_DIR/obj" -name "*.class")
else
    d8 --release --min-api 24 --output "$BUILD_DIR/dex" $(find "$BUILD_DIR/obj" -name "*.class")
fi

# 5. Package & Sign
echo "[*] [4/5] Packaging base APK..."
STAGE_ASSETS=""
if [ -d "$APP_DIR/src/main/assets" ]; then
    STAGE_ASSETS="-A $APP_DIR/src/main/assets"
fi

aapt package -f \\
    -M "$APP_DIR/src/main/AndroidManifest.xml" \\
    -S "$APP_DIR/src/main/res" \\
    -I "$ANDROID_JAR" \\
    $STAGE_ASSETS \\
    -F "$BUILD_DIR/unaligned.apk"

python3 -c "import zipfile; \\
z = zipfile.ZipFile('$BUILD_DIR/unaligned.apk', 'a'); \\
z.write('$BUILD_DIR/dex/classes.dex', 'classes.dex'); z.close()"

echo "[*] [5/5] Aligning and signing APK..."
if command -v zipalign >/dev/null 2>&1; then
    zipalign -v -p 4 "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk" >/dev/null 2>&1 || \\
        cp "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"
else
    cp "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"
fi

apksigner sign --ks "$KEYSTORE" --ks-pass pass:android \\
    --out "$DIST_DIR/app-release.apk" "$BUILD_DIR/aligned.apk"

echo "============================================================"
echo "  BUILD COMPLETE! APK: $DIST_DIR/app-release.apk"
echo "============================================================"
"""

def scaffold(option, out_dir, pkg, name):
    out_dir = os.path.abspath(out_dir)
    pkg_path = pkg.replace(".", "/")
    java_dir = os.path.join(out_dir, "app", "src", "main", "java", pkg_path)
    res_dir = os.path.join(out_dir, "app", "src", "main", "res")
    assets_dir = os.path.join(out_dir, "app", "src", "main", "assets", "web")
    os.makedirs(java_dir, exist_ok=True)
    os.makedirs(os.path.join(res_dir, "values"), exist_ok=True)
    os.makedirs(os.path.join(res_dir, "layout"), exist_ok=True)

    # 1. Manifest
    manifest_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg}">
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:label="{name}"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen">
        <activity
            android:name="{pkg}.MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""
    with open(os.path.join(out_dir, "app", "src", "main", "AndroidManifest.xml"), "w") as f:
        f.write(manifest_xml)

    # 2. strings.xml
    strings_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{name}</string>
</resources>
"""
    with open(os.path.join(res_dir, "values", "strings.xml"), "w") as f:
        f.write(strings_xml)

    # 3. Option 1 vs Option 2
    if option == 1:
        os.makedirs(assets_dir, exist_ok=True)
        # Java WebView host
        main_activity = f"""package {pkg};

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import org.json.JSONObject;

public class MainActivity extends Activity {{
    private WebView webView;

    @Override
    @SuppressLint("SetJavaScriptEnabled")
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);

        webView.addJavascriptInterface(new AppBridge(), "AppBridge");
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("file:///android_asset/web/index.html");
    }}

    public class AppBridge {{
        @JavascriptInterface
        public String getMetricsJson() {{
            try {{
                JSONObject obj = new JSONObject();
                obj.put("tasksCompleted", 128);
                obj.put("uptimeHours", 24.5);
                obj.put("systemHealth", "Optimal");
                return obj.toString();
            }} catch (Exception e) {{
                return "{{}}";
            }}
        }}
    }}
}}
"""
        with open(os.path.join(java_dir, "MainActivity.java"), "w") as f:
            f.write(main_activity)

        # HTML dashboard
        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>{name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #000000; color: #FFFFFF; font-family: -apple-system, sans-serif; padding: 16px; }}
    h1 {{ font-size: 22px; margin-bottom: 16px; color: #FFFFFF; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }}
    .card {{ background: #121212; border: 1px solid #222222; border-radius: 12px; padding: 16px; }}
    .card h3 {{ font-size: 11px; color: #888888; text-transform: uppercase; margin-bottom: 4px; }}
    .card .val {{ font-size: 22px; font-weight: bold; color: #FFC799; }}
    .chart-box {{
      background: #121212;
      border: 1px solid #222222;
      border-radius: 12px;
      padding: 16px;
      height: 220px;
    }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>{name}</h1>
  <div class="grid">
    <div class="card"><h3>Tasks</h3><div id="tasks" class="val">--</div></div>
    <div class="card"><h3>Uptime</h3><div id="uptime" class="val">--</div></div>
  </div>
  <div class="chart-box"><canvas id="myChart"></canvas></div>

  <script>
    document.addEventListener("DOMContentLoaded", function() {{
      let metrics = {{ tasksCompleted: 128, uptimeHours: 24.5 }};
      if (window.AppBridge) {{
        try {{ metrics = JSON.parse(window.AppBridge.getMetricsJson()); }} catch(_) {{}}
      }}
      document.getElementById("tasks").textContent = metrics.tasksCompleted;
      document.getElementById("uptime").textContent = metrics.uptimeHours + "h";

      new Chart(document.getElementById("myChart"), {{
        type: "line",
        data: {{
          labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          datasets: [{{
            label: "Activity",
            data: [15, 22, 18, 30, 42, 38, 55],
            borderColor: "#FFC799",
            tension: 0.3
          }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }}
      }});
    }});
  </script>
</body>
</html>
"""
        with open(os.path.join(assets_dir, "index.html"), "w") as f:
            f.write(index_html)

    else:
        # Option 2: Pure Native Android
        layout_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="#000000"
    android:padding="16dp">

    <TextView
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="{name}"
        android:textColor="#FFFFFF"
        android:textSize="22sp"
        android:textStyle="bold"
        android:layout_marginBottom="16dp" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginBottom="16dp">

        <LinearLayout
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:orientation="vertical"
            android:background="#121212"
            android:padding="16dp">
            <TextView android:text="TASKS" android:textColor="#888888" android:textSize="12sp" />
            <TextView
                android:id="@+id/tvTasks"
                android:text="128"
                android:textColor="#FFC799"
                android:textSize="24sp"
                android:textStyle="bold" />
        </LinearLayout>
    </LinearLayout>

    <view
        class="{pkg}.GraphView"
        android:id="@+id/graphView"
        android:layout_width="match_parent"
        android:layout_height="220dp"
        android:background="#121212" />
</LinearLayout>
"""
        with open(os.path.join(res_dir, "layout", "activity_main.xml"), "w") as f:
            f.write(layout_xml)

        main_activity = f"""package {pkg};

import android.app.Activity;
import android.os.Bundle;

public class MainActivity extends Activity {{
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
    }}
}}
"""
        with open(os.path.join(java_dir, "MainActivity.java"), "w") as f:
            f.write(main_activity)

        graph_view = f"""package {pkg};

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

public class GraphView extends View {{
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float[] data = new float[]{{15, 22, 18, 30, 42, 38, 55}};

    public GraphView(Context context, AttributeSet attrs) {{
        super(context, attrs);
        paint.setColor(Color.parseColor("#FFC799"));
        paint.setStrokeWidth(6f);
        paint.setStyle(Paint.Style.STROKE);
    }}

    @Override
    protected void onDraw(Canvas canvas) {{
        super.onDraw(canvas);
        if (data == null || data.length < 2) return;
        Path path = new Path();
        float w = getWidth();
        float h = getHeight();
        float stepX = w / (data.length - 1);

        for (int i = 0; i < data.length; i++) {{
            float x = i * stepX;
            float y = h - (data[i] / 60f * (h - 40f)) - 20f;
            if (i == 0) path.moveTo(x, y);
            else path.lineTo(x, y);
        }}
        canvas.drawPath(path, paint);
    }}
}}
"""
        with open(os.path.join(java_dir, "GraphView.java"), "w") as f:
            f.write(graph_view)

    # 4. build.sh
    build_sh_path = os.path.join(out_dir, "build.sh")
    with open(build_sh_path, "w") as f:
        f.write(BUILD_SH_TEMPLATE)
    os.chmod(build_sh_path, 0o755)

    print(f"[OK] Successfully scaffolded Option {option} app into: {out_dir}")
    print(f"To build: cd '{out_dir}' && bash build.sh")

def main():
    parser = argparse.ArgumentParser(description="Scaffold Gradle-free Android apps")
    parser.add_argument("--option", type=int, choices=[1, 2], default=1, help="1 for Hybrid Web, 2 for Pure Native")
    parser.add_argument("--out", type=str, required=True, help="Target output directory")
    parser.add_argument("--pkg", type=str, default="com.example.app", help="Package identifier")
    parser.add_argument("--name", type=str, default="My App", help="Application display name")
    args = parser.parse_args()

    scaffold(args.option, args.out, args.pkg, args.name)

if __name__ == "__main__":
    main()
