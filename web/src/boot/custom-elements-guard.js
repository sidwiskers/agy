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
