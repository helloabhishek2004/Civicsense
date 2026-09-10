/**
 * Client-side logging utility with privacy-conscious redaction.
 */
export const logger = {
  info: (message: string, ...args: unknown[]): void => {
    console.log(`[CivicSense:INFO] ${message}`, ...args);
  },
  warn: (message: string, ...args: unknown[]): void => {
    console.warn(`[CivicSense:WARN] ${message}`, ...args);
  },
  error: (message: string, ...args: unknown[]): void => {
    console.error(`[CivicSense:ERROR] ${message}`, ...args);
  },
  debug: (message: string, ...args: unknown[]): void => {
    if (__DEV__) {
      console.debug(`[CivicSense:DEBUG] ${message}`, ...args);
    }
  },
};
