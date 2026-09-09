<script setup lang="ts">
import ServerSettings from './platform/ServerSettings.vue'
import { nativeApp } from './platform/native'
</script>
<template>
  <RouterView />
  <ServerSettings v-if="nativeApp" />
</template>
