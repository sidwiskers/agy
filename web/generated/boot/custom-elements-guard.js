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


})();
