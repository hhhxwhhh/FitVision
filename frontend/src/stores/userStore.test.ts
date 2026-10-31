import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/userStore'

// The real api module touches browser globals at import time, so we replace it
// with a tiny stub exposing the single method the store uses. `vi.hoisted`
// ensures the mock factory can reference it even though `vi.mock` is hoisted.
const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))
vi.mock('@/api', () => ({
  default: { get: mockGet },
}))

const sampleUser = {
  id: 1,
  username: 'bob',
  nickname: 'Bob',
  email: 'bob@example.com',
  avatar: 'http://example.com/a.png',
}

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGet.mockReset()
    localStorage.clear()
  })

  it('is not authenticated before a user is loaded', () => {
    const store = useUserStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.userName).toBe('')
    expect(store.userAvatar).toBe('')
  })

  it('derives userName from nickname, then username', () => {
    const store = useUserStore()
    store.user = { ...sampleUser, nickname: 'Bobby' }
    expect(store.userName).toBe('Bobby')
    store.user = { ...sampleUser, nickname: '' }
    expect(store.userName).toBe('bob')
  })

  it('fetchUser stores the user and caches name/avatar in localStorage', async () => {
    mockGet.mockResolvedValue({ data: sampleUser })
    const store = useUserStore()
    await store.fetchUser()
    expect(store.isAuthenticated).toBe(true)
    expect(store.user?.username).toBe('bob')
    expect(localStorage.getItem('username')).toBe('Bob')
    expect(localStorage.getItem('user_avatar')).toBe('http://example.com/a.png')
  })

  it('fetchUser clears the user when the request fails', async () => {
    mockGet.mockRejectedValue(new Error('401'))
    const store = useUserStore()
    store.user = { ...sampleUser }
    await store.fetchUser()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('logout clears the user and the stored token', () => {
    const store = useUserStore()
    store.user = { ...sampleUser }
    localStorage.setItem('jwt_token', 'secret')
    store.logout()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('jwt_token')).toBeNull()
  })
})
