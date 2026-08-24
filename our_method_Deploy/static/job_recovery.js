(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.PlcJobRecovery = api;
}(typeof window !== 'undefined' ? window : globalThis, function () {
  const KEY = 'plc-generation.active-job-id';
  const SUBMISSION_KEY = 'plc-generation.pending-submission-key';
  const PENDING_REQUEST_KEY = 'plc-generation.pending-submission';

  function save(storage, jobId) {
    if (storage && typeof jobId === 'string' && jobId) storage.setItem(KEY, jobId);
  }

  function load(storage) {
    if (!storage) return null;
    const value = storage.getItem(KEY);
    return typeof value === 'string' && value ? value : null;
  }

  function clear(storage) {
    if (storage) storage.removeItem(KEY);
  }

  function saveSubmission(storage, key) {
    if (storage && typeof key === 'string' && key) storage.setItem(SUBMISSION_KEY, key);
  }

  function loadSubmission(storage) {
    if (!storage) return null;
    const value = storage.getItem(SUBMISSION_KEY);
    return typeof value === 'string' && value ? value : null;
  }

  function clearSubmission(storage) {
    if (storage) storage.removeItem(SUBMISSION_KEY);
  }

  function savePending(storage, key, request) {
    if (!storage || typeof key !== 'string' || !key || !request) return;
    storage.setItem(PENDING_REQUEST_KEY, JSON.stringify({key, request}));
  }

  function loadPending(storage) {
    if (!storage) return null;
    const value = storage.getItem(PENDING_REQUEST_KEY);
    if (typeof value !== 'string' || !value) return null;
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed.key === 'string' && parsed.key && parsed.request
        ? parsed : null;
    } catch (_error) {
      return null;
    }
  }

  function clearPending(storage) {
    if (storage) storage.removeItem(PENDING_REQUEST_KEY);
  }

  function reconnectDelay(failures) {
    const count = Math.max(1, Number(failures) || 1);
    return Math.min(30000, 2000 * (2 ** Math.min(4, count - 1)));
  }

  return {
    KEY, SUBMISSION_KEY, PENDING_REQUEST_KEY,
    save, load, clear,
    saveSubmission, loadSubmission, clearSubmission,
    savePending, loadPending, clearPending, reconnectDelay,
  };
}));
