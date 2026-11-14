---
name: native-android-builder
description: >-
  Fast, Gradle-free Native & Hybrid Android App & Dashboard Builder.
  Builds and packages high-performance APKs in seconds directly on device using raw
  Android SDK CLI tools (AAPT, Javac, D8, APKSigner). Covers Option 1 (Modern Web/Hybrid
  Dashboard & App via Hardware-Accelerated WebView + Bridge) and Option 2 (100% Pure
  Native Java + XML Layouts + Custom Canvas Graph Views + SQLite).
---

# Fast Gradle-Free Android Builder (`native-android-builder`)

> [!IMPORTANT]
> This skill enables building, compiling, and signing production-grade Android APKs
> directly on a mobile device or Linux machine in **under 30 seconds**, completely bypassing
> Gradle daemons, Groovy/Kotlin script evaluation, and massive memory overhead.

---

## 1. Architectural Choice: Option 1 vs. Option 2

Choose the right architecture based on what you are building:

| Dimension | Option 1: Modern Web / Hybrid Dashboard | Option 2: Pure Native (Java + XML + Canvas) |
| :--- | :--- | :--- |
| **Best For** | Visual dashboards, interactive charts, telemetry, responsive layouts | Metric cards, lists, status monitors, system utilities |
| **UI Technology** | HTML5, CSS3, JS, Canvas/SVG, Chart.js, Tailwind | Native Android XML layouts, `RecyclerView`, Custom Canvas `View` |
| **Host Container** | Hardware-accelerated `android.webkit.WebView` | Native `Activity` / `View` tree |
| **Data Bridge** | `@JavascriptInterface` (Java <-> JS two-way IPC) | Direct Java in-memory calls / `android.database.sqlite` |
| **Theme / AMOLED** | Pure CSS `#000000`, Flexbox/Grid, Desktop Mode toggle | Native XML themes (`SplashThemeDark`), ripple drawables |
| **Build Time** | ~5s web bundle + ~15s APK package | ~15s direct Java compile + DEX |

---

## 2. The 5-Phase Direct Build Pipeline (No Gradle)

Both Option 1 and Option 2 use the same blazing-fast CLI pipeline:

```
[ Phase 1: Config & Manifest ]
       │  Generates BuildConfig.java, AndroidManifest.xml, and values/gen.xml
       ▼
[ Phase 2: Resource Compilation (AAPT) ]
       │  aapt package -m -J <gen_dir> -M <manifest> -S <res_dir> -I <android.jar>
       │  Compiles XML layouts, drawables, and strings into R.java (< 1 second)
       ▼
[ Phase 3: Java Compilation (Javac) ]
       │  javac -source 1.8 -target 1.8 -d <obj_dir> -cp <android.jar> @sources.txt
       │  Compiles all Java source code directly into .class bytecode (2–3 seconds)
       ▼
[ Phase 4: Bytecode Dexing (Google D8) ]
       │  java -jar r8.jar d8 --release --min-api 24 --output <dex_dir> <classes...>
       │  Converts .class bytecode directly into classes.dex (~1 second)
       ▼
[ Phase 5: Packaging, Alignment & Signing ]
          aapt package -F unaligned.apk -M <manifest> -S <res> -I <android.jar>
          zip -u unaligned.apk classes.dex assets/...
          zipalign -v -p 4 unaligned.apk aligned.apk
          apksigner sign --ks debug.keystore aligned.apk -> final.apk
```

---

## 3. Option 1 Blueprint: Modern Web/Hybrid Dashboard

### A. Java WebView Host (`MainActivity.java` or `DashboardActivity.java`)
```java
package com.mycompany.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import org.json.JSONObject;

public class DashboardActivity extends Activity {
    private WebView webView;

    @Override
    @SuppressLint("SetJavaScriptEnabled")
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);

        // Bridge connecting Java to Web Dashboard
        webView.addJavascriptInterface(new DashboardBridge(), "DashboardBridge");
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("file:///android_asset/web/dashboard.html");
    }

    public class DashboardBridge {
        @JavascriptInterface
        public String getUserDataJson() {
            try {
                JSONObject data = new JSONObject();
                data.put("totalTasks", 142);
                data.put("uptimeHours", 18.5);
                data.put("batteryLevel", 87);
                return data.toString();
            } catch (Exception e) {
                return "{}";
            }
        }
    }
}
```

### B. Responsive AMOLED Dashboard (`dashboard.html`)
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #000000; color: #FFFFFF; font-family: -apple-system, sans-serif; padding: 16px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
    .card { background: #121212; border: 1px solid #222222; border-radius: 12px; padding: 16px; }
    .card h3 { font-size: 12px; color: #888888; text-transform: uppercase; margin-bottom: 6px; }
    .card .val { font-size: 24px; font-weight: bold; color: #FFC799; }
    .chart-box { background: #121212; border: 1px solid #222222; border-radius: 12px; padding: 16px; height: 220px; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <div class="grid">
    <div class="card"><h3>Total Tasks</h3><div id="tasks" class="val">--</div></div>
    <div class="card"><h3>Uptime</h3><div id="uptime" class="val">--</div></div>
  </div>
  <div class="chart-box"><canvas id="chartCanvas"></canvas></div>

  <script>
    document.addEventListener("DOMContentLoaded", function() {
      let data = { totalTasks: 142, uptimeHours: 18.5 };
      if (window.DashboardBridge) {
        try { data = JSON.parse(window.DashboardBridge.getUserDataJson()); } catch(_) {}
      }
      document.getElementById("tasks").textContent = data.totalTasks;
      document.getElementById("uptime").textContent = data.uptimeHours + "h";

      new Chart(document.getElementById("chartCanvas"), {
        type: "line",
        data: {
          labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          datasets: [{ label: "Activity", data: [12, 19, 15, 25, 32, 28, 40], borderColor: "#FFC799", tension: 0.3 }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
      });
    });
  </script>
</body>
</html>
```

---

## 4. Option 2 Blueprint: Pure Native Android (Java + XML + Canvas)

### A. Native XML Layout (`res/layout/activity_dashboard.xml`)
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:background="#000000"
    android:padding="16dp">

    <TextView
        android:id="@+id/tvTitle"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:text="System Dashboard"
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
            android:padding="12dp">
            <TextView android:text="TASKS" android:textColor="#888888" android:textSize="12sp" />
            <TextView android:id="@+id/tvTaskCount" android:text="142" android:textColor="#FFC799" android:textSize="24sp" android:textStyle="bold" />
        </LinearLayout>
    </LinearLayout>

    <!-- Custom Canvas Graph View -->
    <view
        class="com.mycompany.app.GraphView"
        android:id="@+id/graphView"
        android:layout_width="match_parent"
        android:layout_height="200dp"
        android:background="#121212" />
</LinearLayout>
```

### B. Custom Canvas 2D Graph (`GraphView.java`)
```java
package com.mycompany.app;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.View;

public class GraphView extends View {
    private final Paint linePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float[] points = new float[]{10, 45, 25, 60, 50, 85, 70, 95};

    public GraphView(Context context, AttributeSet attrs) {
        super(context, attrs);
        linePaint.setColor(Color.parseColor("#FFC799"));
        linePaint.setStrokeWidth(6f);
        linePaint.setStyle(Paint.Style.STROKE);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (points == null || points.length < 2) return;
        Path path = new Path();
        float w = getWidth();
        float h = getHeight();
        float stepX = w / (points.length - 1);

        for (int i = 0; i < points.length; i++) {
            float x = i * stepX;
            float y = h - (points[i] / 100f * (h - 40f)) - 20f;
            if (i == 0) path.moveTo(x, y);
            else path.lineTo(x, y);
        }
        canvas.drawPath(path, linePaint);
    }
}
```

---

## 5. Instant Scaffolding CLI

Use the built-in scaffolding tool to generate a complete working app of either option in seconds:

```bash
# Scaffold an Option 1 (Hybrid WebView + Chart.js) app:
python3 /data/user/0/com.agy/files/.gemini/config/skills/native-android-builder/scripts/scaffold_app.py --option 1 --out my-hybrid-app --pkg com.example.hybrid

# Scaffold an Option 2 (Pure Native Java + XML + Canvas) app:
python3 /data/user/0/com.agy/files/.gemini/config/skills/native-android-builder/scripts/scaffold_app.py --option 2 --out my-native-app --pkg com.example.native

# Build the APK in 20 seconds:
cd my-hybrid-app && bash build.sh
```
