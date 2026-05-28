import { describe, expect, it, vi } from "vitest";
import { createDebouncedAction } from "./debounce";

describe("createDebouncedAction", () => {
  it("does not fire on every keystroke-style trigger", () => {
    vi.useFakeTimers();
    const action = vi.fn();
    const debounced = createDebouncedAction<string>(1800, action);

    debounced.trigger("a");
    debounced.trigger("ab");
    debounced.trigger("abc");

    vi.advanceTimersByTime(1799);
    expect(action).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(action).toHaveBeenCalledTimes(1);
    expect(action).toHaveBeenCalledWith("abc");

    vi.useRealTimers();
  });
});
