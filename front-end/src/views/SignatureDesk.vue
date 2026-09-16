<script setup lang="ts">
import { useRouter } from 'vue-router'
import WorkflowDesk from '@/features/forest-portal/components/WorkflowDesk.vue'
const router = useRouter()
</script>
<template><main class="signature-clearing"><WorkflowDesk mode="secondary" @close="router.push('/login')" /></main></template>
<style scoped>.signature-clearing { min-height: 100dvh; background: radial-gradient(ellipse at 20% 90%, #405e65, transparent 65%), linear-gradient(120deg, #a5af92, #e6dfc2); }</style>
