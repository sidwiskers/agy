// Workaround for custom elements in overlay bundle.
// Re-defining an already-registered custom element throws; swallow the second
// define so both the host and the overlay bundle can register safely.
if (window.customElements) {
  var originalDefine = window.customElements.define;
  window.customElements.define = function (name, constructor, options) {
    if (!window.customElements.get(name)) {
      originalDefine.call(window.customElements, name, constructor, options);
    }
  };
}

// Keep webview alive and prevent hidden throttling when backgrounded
try {
  Object.defineProperty(document, 'hidden', {
    get: function() { return false; },
    configurable: true
  });
  Object.defineProperty(document, 'visibilityState', {
    get: function() { return 'visible'; },
    configurable: true
  });
  document.addEventListener('visibilitychange', function(e) {
    if (document.visibilityState !== 'visible') {
      e.stopImmediatePropagation();
    }
  }, true);

  window.addEventListener('agy:host-resume', function() {
    try {
      window.dispatchEvent(new Event('resize'));
      window.dispatchEvent(new Event('focus'));
      if (document.body) {
        document.body.style.transform = 'translateZ(0)';
        requestAnimationFrame(function() {
          document.body.style.transform = '';
        });
      }
    } catch (_) {}
  });
} catch (_) {}

// Native Android notifications bridge for Antigravity web UI
if (!window.nativeNotifications) {
  var notificationListeners = [];
  window.nativeNotifications = {
    send: function (notification) {
      if (!notification) return Promise.resolve(true);
      var title = notification.title || 'Antigravity';
      var body = notification.body || notification.message || 'Task completed';
      var text = title + ': ' + body;

      if (window.Android && typeof window.Android.showToast === 'function') {
        window.Android.showToast(text, true);
      } else {
        try {
          fetch('http://127.0.0.1:45160/gateway', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: 'toast',
              payload: { message: text, duration: 'long', sound: true }
            })
          }).catch(function () {});
        } catch (_) {}
      }
      return Promise.resolve(true);
    },
    updateProgress: function (title, status, isGenerating) {
      if (window.Android && typeof window.Android.updateNotificationProgress === 'function') {
        window.Android.updateNotificationProgress(title, status, !!isGenerating);
      }
      return Promise.resolve(true);
    },
    onClicked: function (cb) {
      if (typeof cb === 'function') {
        notificationListeners.push(cb);
      }
    },
    openSystemPreferences: function () {
      return Promise.resolve(true);
    },
    clearNotifications: function () {
      return Promise.resolve(true);
    }
  };
}

// Android Share Sheet Receiver (ACTION_SEND)
(function() {
  function fillPromptBox(text) {
    if (!text) return false;
    var input = document.querySelector('textarea, [contenteditable="true"]');
    if (input) {
      if (input.tagName === 'TEXTAREA') {
        input.value = (input.value ? input.value + '\n\n' : '') + text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        input.innerText = (input.innerText ? input.innerText + '\n\n' : '') + text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
      input.focus();
      return true;
    }
    return false;
  }

  window.addEventListener('agy:shared-content', function(e) {
    var text = (e && e.detail && e.detail.text) || window.__AG_PENDING_SHARE__;
    if (!text) return;
    if (!fillPromptBox(text)) {
      var attempts = 0;
      var timer = setInterval(function() {
        attempts++;
        if (fillPromptBox(text) || attempts > 25) {
          clearInterval(timer);
          window.__AG_PENDING_SHARE__ = null;
        }
      }, 400);
    } else {
      window.__AG_PENDING_SHARE__ = null;
    }
  });

  window.addEventListener('load', function() {
    setTimeout(function() {
      if (window.Android && typeof window.Android.getPendingSharedText === 'function') {
        var pending = window.Android.getPendingSharedText();
        if (pending && pending.length > 0) {
          window.dispatchEvent(new CustomEvent('agy:shared-content', { detail: { text: pending } }));
          window.Android.clearPendingSharedText();
        }
      }
    }, 1200);
  });
})();

// Live Lockscreen & Notification Shade Progress Tracker
(function() {
  var _lastReportedTitle = "";
  var _lastReportedStatus = "";
  var _lastReportedGenerating = null;

  function updateAgentProgressFromState(state) {
    if (!state || typeof state !== "object") return;

    // Check status: 2 = RUNNING, 3 = BUSY, 4 = CANCELING, 1 = IDLE
    var isRunning = state.status === 2 || state.status === 3;

    // Subagent status check
    if (!isRunning && state.subagentStates) {
      var subKeys = Object.keys(state.subagentStates);
      for (var i = 0; i < subKeys.length; i++) {
        var sa = state.subagentStates[subKeys[i]];
        if (sa && (sa.status === 2 || sa.status === 3)) {
          isRunning = true;
          break;
        }
      }
    }

    // Background tasks check
    if (!isRunning && Array.isArray(state.backgroundTasks) && state.backgroundTasks.length > 0) {
      isRunning = true;
    }

    var title = "";
    var description = "";

    if (isRunning) {
      title = "Antigravity • Generating...";

      // 1. Try to find active subagent details
      if (state.subagentStates) {
        var subKeys = Object.keys(state.subagentStates);
        for (var i = 0; i < subKeys.length; i++) {
          var sa = state.subagentStates[subKeys[i]];
          if (sa && (sa.status === 2 || sa.status === 3)) {
            var saRole = sa.role || sa.subagentName || "Subagent";
            var saAction = sa.liveToolSummary || sa.toolSummary || sa.waitingStepSummary || "";
            description = saRole + (saAction ? ": " + saAction : " running");
            break;
          }
        }
      }

      // 2. If no subagent, extract from latest step of main trajectory
      if (!description && state.trajectorySlice && Array.isArray(state.trajectorySlice.stepsInSlice)) {
        var steps = state.trajectorySlice.stepsInSlice;
        for (var j = steps.length - 1; j >= 0; j--) {
          var s = steps[j];
          if (!s) continue;

          var meta = s.metadata || {};
          if (meta.toolAction) {
            description = meta.toolAction;
            break;
          }
          if (meta.toolSummary) {
            description = meta.toolSummary;
            break;
          }
          if (meta.toolCall && meta.toolCall.name) {
            description = "Using tool: " + meta.toolCall.name;
            break;
          }
          if (s.taskDetails && s.taskDetails.title) {
            description = s.taskDetails.title;
            break;
          }
          if (s.step) {
            var sc = s.step.case;
            var sv = s.step.value;
            if (sc === "plannerResponse") {
              if (sv && (sv.thinking || sv.rawThinking)) {
                description = "Thinking...";
                break;
              } else if (sv && sv.response) {
                description = "Writing response...";
                break;
              }
            } else if (sc === "generic") {
              var ri = sv && sv.result && sv.result.stepRenderInfo;
              if (ri && ri.title) {
                description = (ri.titlePrefix ? ri.titlePrefix + " " : "") + ri.title;
                break;
              }
              description = "Executing action...";
              break;
            }
          }
        }
      }

      // 3. Background tasks fallback
      if (!description && Array.isArray(state.backgroundTasks) && state.backgroundTasks.length > 0) {
        var bg = state.backgroundTasks[0];
        var snap = bg && bg.taskSnapshot;
        description = (snap && (snap.toolAction || snap.toolSummary || snap.description)) || "Background task running...";
      }

      if (!description) {
        description = "Generating response...";
      }
    } else {
      if (state.status === 1) {
        title = "Antigravity";
        description = "Task completed";
      } else {
        title = "Antigravity";
        description = "Core active";
      }
    }

    if (_lastReportedTitle === title && _lastReportedStatus === description && _lastReportedGenerating === isRunning) {
      return;
    }
    _lastReportedTitle = title;
    _lastReportedStatus = description;
    _lastReportedGenerating = isRunning;

    if (window.Android && typeof window.Android.updateNotificationProgress === "function") {
      try {
        window.Android.updateNotificationProgress(title, description, isRunning);
      } catch (_) {}
    }
  }

  window.__agUpdateProgress = updateAgentProgressFromState;
})();
