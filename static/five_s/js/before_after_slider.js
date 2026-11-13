/* ==========================================================================
   Before/After Image Slider — 5S Module
   - Pointer events (mouse / touch / pen)
   - Click anywhere on the frame to jump
   - Keyboard: ←/→ arrow keys, Home, End
   - Multiple sliders per page supported
   ========================================================================== */
(function () {
  'use strict';

  function initSlider(root) {
    // root is the .ba-slider element, frame is inside
    const frame = root.querySelector('.ba-slider__frame');
    const handle = root.querySelector('.ba-slider__handle');
    if (!frame || !handle) return;
    if (root.dataset.baInitialized === '1') return;
    root.dataset.baInitialized = '1';

    let dragging = false;
    let rafId = null;
    let pendingPos = null;

    function applyPos(percent) {
      const clamped = Math.max(0, Math.min(100, percent));
      frame.style.setProperty('--ba-pos', clamped + '%');
      handle.setAttribute('aria-valuenow', Math.round(clamped));
    }

    function setPos(percent) {
      pendingPos = percent;
      if (rafId) return;
      rafId = requestAnimationFrame(function () {
        rafId = null;
        if (pendingPos !== null) {
          applyPos(pendingPos);
          pendingPos = null;
        }
      });
    }

    function posFromEvent(e) {
      const rect = frame.getBoundingClientRect();
      const clientX = e.touches && e.touches.length
        ? e.touches[0].clientX
        : e.clientX;
      return ((clientX - rect.left) / rect.width) * 100;
    }

    function onDown(e) {
      // Ignore right-click / middle-click
      if (e.button !== undefined && e.button !== 0 && e.pointerType === 'mouse') {
        return;
      }
      dragging = true;
      try {
        frame.setPointerCapture(e.pointerId);
      } catch (err) {
        /* older browsers */
      }
      setPos(posFromEvent(e));
      e.preventDefault();
    }

    function onMove(e) {
      if (!dragging) return;
      setPos(posFromEvent(e));
      e.preventDefault();
    }

    function onUp(e) {
      if (!dragging) return;
      dragging = false;
      try {
        frame.releasePointerCapture(e.pointerId);
      } catch (err) {
        /* ignore */
      }
    }

    // Pointer events cover mouse + touch + pen
    frame.addEventListener('pointerdown', onDown);
    frame.addEventListener('pointermove', onMove);
    frame.addEventListener('pointerup', onUp);
    frame.addEventListener('pointercancel', onUp);

    // Click anywhere to jump (only if not already dragging)
    frame.addEventListener('click', function (e) {
      if (!dragging) {
        setPos(posFromEvent(e));
      }
    });

    // Keyboard accessibility on the handle
    handle.addEventListener('keydown', function (e) {
      const cur = parseFloat(frame.style.getPropertyValue('--ba-pos')) || 50;
      let next = null;
      switch (e.key) {
        case 'ArrowLeft':
          next = cur - 2;
          break;
        case 'ArrowRight':
          next = cur + 2;
          break;
        case 'Home':
          next = 0;
          break;
        case 'End':
          next = 100;
          break;
        default:
          return;
      }
      e.preventDefault();
      setPos(next);
    });

    // Initialize at 50 %
    applyPos(50);
  }

  function initAll() {
    document.querySelectorAll('[data-ba-slider]').forEach(initSlider);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // Expose for dynamically-injected content (modals, AJAX)
  window.initBeforeAfterSliders = initAll;
})();