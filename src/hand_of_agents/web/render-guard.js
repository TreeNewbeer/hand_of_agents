export function createRenderGuard(render, isExternallyBlocked = () => false, schedule = null) {
  const activeInteractions = new Set();
  const scheduleTask = schedule ?? ((callback) => window.setTimeout(callback, 0));
  let renderPending = false;

  function requestRender() {
    if (activeInteractions.size > 0 || isExternallyBlocked()) {
      renderPending = true;
      return false;
    }
    renderPending = false;
    render();
    return true;
  }

  function beginInteraction(interactionId) {
    activeInteractions.add(interactionId);
  }

  function endInteraction(interactionId) {
    if (!activeInteractions.has(interactionId)) return;
    // Keep rendering blocked through the click/default action generated after
    // pointerup or keyup. Replacing the target before then drops the click.
    scheduleTask(() => {
      activeInteractions.delete(interactionId);
      if (renderPending) requestRender();
    });
  }

  function cancelInteractions() {
    activeInteractions.clear();
    if (renderPending) requestRender();
  }

  function flush() {
    if (renderPending) requestRender();
  }

  return {
    beginInteraction,
    cancelInteractions,
    endInteraction,
    flush,
    requestRender,
  };
}
