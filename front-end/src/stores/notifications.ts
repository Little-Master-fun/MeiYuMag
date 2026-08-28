import { defineStore } from 'pinia'
import { ref } from 'vue'

export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message?: string
  duration?: number
}

export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<Notification[]>([])

  function add(n: Omit<Notification, 'id'>) {
    const id = Math.random().toString(36).slice(2)
    items.value.push({ id, ...n })
    if (n.duration !== 0) {
      setTimeout(() => remove(id), n.duration ?? 4000)
    }
    return id
  }

  function remove(id: string) {
    const idx = items.value.findIndex((n) => n.id === id)
    if (idx !== -1) items.value.splice(idx, 1)
  }

  const success = (title: string, message?: string) => add({ type: 'success', title, message })
  const error   = (title: string, message?: string) => add({ type: 'error',   title, message })
  const warning = (title: string, message?: string) => add({ type: 'warning', title, message })
  const info    = (title: string, message?: string) => add({ type: 'info',    title, message })

  return { items, add, remove, success, error, warning, info }
})
