export function createDebouncedAction<T>(
  delayMs: number,
  action: (value: T) => void
) {
  let handle: number | undefined;

  return {
    trigger(value: T) {
      if (handle !== undefined) {
        window.clearTimeout(handle);
      }
      handle = window.setTimeout(() => action(value), delayMs);
    },
    cancel() {
      if (handle !== undefined) {
        window.clearTimeout(handle);
        handle = undefined;
      }
    },
  };
}
