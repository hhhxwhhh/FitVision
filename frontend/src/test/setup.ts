// Test environment shims.
// The unit tests run under Vitest's Node environment. The app code touches a few
// browser globals (notably localStorage), so we polyfill just enough of them to
// exercise stores and utilities without pulling in jsdom.

class MemoryStorage {
  private store = new Map<string, string>()

  get length(): number {
    return this.store.size
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value))
  }

  removeItem(key: string): void {
    this.store.delete(key)
  }

  clear(): void {
    this.store.clear()
  }
}

if (!('localStorage' in globalThis)) {
  globalThis.localStorage = new MemoryStorage()
}

export {}
