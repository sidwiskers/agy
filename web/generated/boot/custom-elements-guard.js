(function(){
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
// Live Lockscreen & Notification Shade Progress Tracker
(function() {
  var _lastReportedTitle = "";
  var _lastReportedStatus = "";
  var _lastReportedGenerating = null;

  function isStateRunning(state) {
    if (!state || typeof state !== "object") return false;
    // 1. Explicit status check: 2 = RUNNING, 4 = BUSY, 3 = CANCELING
    if (state.status === 2 || state.status === 4 || state.status === 3) return true;
    if (state.executionStatus === 2) return true;

    // 2. FullyIdle flag
    if (state.fullyIdle === false) return true;

    // 3. Step statuses check
    var steps = state.trajectorySlice && state.trajectorySlice.stepsInSlice;
    if (Array.isArray(steps) && steps.length > 0) {
      for (var i = steps.length - 1; i >= Math.max(0, steps.length - 8); i--) {
        var st = steps[i];
        if (st && (st.status === 2 || st.status === 8 || st.status === 9 || st.status === 11)) {
          return true;
        }
      }
    }

    // 4. Subagent check
    if (state.subagentStates) {
      for (var k in state.subagentStates) {
        var sa = state.subagentStates[k];
        if (sa && (sa.status === 2 || sa.status === 4 || sa.status === 3 || sa.fullyIdle === false)) {
          return true;
        }
      }
    }

    // 5. Background tasks check
    if (Array.isArray(state.backgroundTasks) && state.backgroundTasks.length > 0) {
      for (var j = 0; j < state.backgroundTasks.length; j++) {
        var bg = state.backgroundTasks[j];
        if (bg && (bg.isRunning || (bg.taskSnapshot && bg.taskSnapshot.isRunning))) {
          return true;
        }
      }
    }

    return false;
  }

  function getStatusDescription(state) {
    // 1. Check active subagents
    if (state.subagentStates) {
      for (var sid in state.subagentStates) {
        var sa = state.subagentStates[sid];
        if (sa && (sa.status === 2 || sa.status === 4 || sa.fullyIdle === false)) {
          var saName = sa.subagentName || sa.role || "Subagent";
          var saAction = sa.liveToolSummary || sa.toolSummary || sa.waitingStepSummary || "";
          return saName + (saAction ? ": " + saAction : " running");
        }
      }
    }

    // 2. Check steps in reverse
    var steps = state.trajectorySlice && state.trajectorySlice.stepsInSlice;
    if (Array.isArray(steps) && steps.length > 0) {
      for (var i = steps.length - 1; i >= 0; i--) {
        var s = steps[i];
        if (!s) continue;

        var meta = s.metadata || {};
        var toolAction = meta.toolAction;
        var toolSummary = meta.toolSummary;

        if ((!toolAction || !toolSummary) && meta.toolCall && meta.toolCall.argumentsJson) {
          try {
            var args = JSON.parse(meta.toolCall.argumentsJson);
            if (!toolAction && typeof args.toolAction === "string") toolAction = args.toolAction;
            if (!toolSummary && typeof args.toolSummary === "string") toolSummary = args.toolSummary;
          } catch (_) {}
        }

        if (toolAction && toolSummary) {
          return toolAction + " (" + toolSummary + ")";
        }
        if (toolAction) return toolAction;
        if (toolSummary) return toolSummary;
        if (meta.toolCall && meta.toolCall.name) {
          return "Using tool: " + meta.toolCall.name;
        }
        if (s.taskDetails && s.taskDetails.title) {
          return s.taskDetails.title;
        }

        if (s.step) {
          if (s.step.case === "plannerResponse") {
            var pv = s.step.value;
            if (pv && (pv.thinking || pv.rawThinking)) {
              return "Thinking...";
            }
            if (pv && pv.response) {
              return "Writing response...";
            }
          } else if (s.step.case === "generic") {
            var ri = s.step.value && s.step.value.result && s.step.value.result.stepRenderInfo;
            if (ri && ri.title) {
              return (ri.titlePrefix ? ri.titlePrefix + " " : "") + ri.title;
            }
            return "Executing tool...";
          }
        }
      }
    }

    // 3. Background tasks fallback
    if (Array.isArray(state.backgroundTasks) && state.backgroundTasks.length > 0) {
      var bg = state.backgroundTasks[0];
      var snap = bg && bg.taskSnapshot;
      return (snap && (snap.toolAction || snap.toolSummary || snap.description)) || "Background task running...";
    }

    return "Generating response...";
  }

  function updateAgentProgressFromState(state) {
    if (!state || typeof state !== "object") return;

    var isRunning = isStateRunning(state);
    var title = "";
    var description = "";

    if (isRunning) {
      title = "Antigravity • Generating...";
      description = getStatusDescription(state);
    } else {
      if (state.status === 1 || state.fullyIdle === true) {
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

  // Background poller as resilient safety net
  setInterval(function() {
    try {
      if (window.__agTrajManager && typeof window.__agTrajManager.getAgentStates === 'function') {
        var map = window.__agTrajManager.getAgentStates();
        if (map && map.size > 0) {
          for (var entry of map.values()) {
            if (entry && entry.provider && typeof entry.provider.getState === 'function') {
              var st = entry.provider.getState();
              if (st) {
                updateAgentProgressFromState(st);
              }
            }
          }
        }
      }
    } catch (_) {}
  }, 1000);
})();


})();
