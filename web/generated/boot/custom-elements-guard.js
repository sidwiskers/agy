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


})();
