"use client";

import { useSyncExternalStore } from "react";

export const SERVER_SNAPSHOT = "__RAINASSESS_SERVER__";

function subscribe(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  return () => window.removeEventListener("storage", onStoreChange);
}

export function useSessionValue(key: string): string | null {
  return useSyncExternalStore(
    subscribe,
    () => sessionStorage.getItem(key),
    () => SERVER_SNAPSHOT,
  );
}

