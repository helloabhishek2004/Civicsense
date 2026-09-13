import '@testing-library/jest-dom';

if (typeof window !== 'undefined' && typeof globalThis !== 'undefined') {
  if (globalThis.AbortController) {
    window.AbortController = globalThis.AbortController;
  }
  if (globalThis.AbortSignal) {
    window.AbortSignal = globalThis.AbortSignal;
  }
}
