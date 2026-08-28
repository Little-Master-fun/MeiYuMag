<script setup lang="ts">
import { useNotificationsStore } from '@/stores/notifications'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next'

const store = useNotificationsStore()

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const styles = {
  success: 'border-jade-500/40 bg-jade-500/10 text-jade-300',
  error:   'border-red-500/40  bg-red-500/10  text-red-300',
  warning: 'border-gold-400/40 bg-gold-400/10 text-gold-300',
  info:    'border-blue-500/40 bg-blue-500/10 text-blue-300',
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-5 right-5 z-[9999] flex flex-col gap-3 pointer-events-none" style="min-width:320px;max-width:420px">
      <TransitionGroup name="toast" tag="div" class="flex flex-col gap-3">
        <div
          v-for="n in store.items"
          :key="n.id"
          class="pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl backdrop-blur-xl"
          :class="styles[n.type]"
        >
          <component :is="icons[n.type]" class="shrink-0 mt-0.5" :size="18" />
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-sm leading-snug">{{ n.title }}</p>
            <p v-if="n.message" class="text-xs opacity-80 mt-0.5 leading-relaxed">{{ n.message }}</p>
          </div>
          <button
            class="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
            @click="store.remove(n.id)"
          >
            <X :size="16" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.92);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.9);
  max-height: 0;
  margin: 0;
  padding: 0;
}
</style>
