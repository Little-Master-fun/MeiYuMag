<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const venueName = computed(() => String(route.query.venueName || '所选场地'))
const applicationDate = computed(() => String(route.query.date || '待选择日期'))
</script>

<template>
  <main class="application-placeholder">
    <button type="button" class="back-button" @click="router.back()">
      ← 返回场地日历
    </button>
    <section aria-labelledby="placeholder-title" class="placeholder-card">
      <p class="eyebrow">MEIYU · VENUE APPLICATION</p>
      <h1 id="placeholder-title">场地申请提交</h1>
      <p>{{ venueName }} · {{ applicationDate }}</p>
      <span>申请表单将在这里继续开发</span>
    </section>
  </main>
</template>

<style scoped>
.application-placeholder {
  min-height: 100vh;
  padding: 28px;
  background: #f5ecd9;
  color: #58452f;
  font-family: 'Songti SC', 'STSong', serif;
}

.back-button {
  border: 1px solid rgba(91, 113, 88, 0.38);
  border-radius: 14px 5px 14px 5px;
  padding: 9px 14px;
  background: rgba(255, 252, 239, 0.72);
  color: #526652;
  cursor: pointer;
}

.placeholder-card {
  width: min(560px, calc(100vw - 56px));
  margin: 22vh auto 0;
  padding: 48px;
  border: 1px solid rgba(117, 86, 47, 0.2);
  border-radius: 5px 22px 5px 22px;
  background: rgba(238, 220, 172, 0.46);
  box-shadow: 0 24px 70px rgba(74, 57, 32, 0.12);
}

.eyebrow {
  margin: 0 0 18px;
  color: rgba(89, 70, 47, 0.58);
  font-family: Georgia, serif;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.1em;
}

h1 {
  margin: 0 0 18px;
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 600;
}

.placeholder-card > p:not(.eyebrow) {
  margin: 0 0 12px;
  font-size: 20px;
}

.placeholder-card span {
  color: rgba(77, 60, 40, 0.55);
  font-size: 15px;
}
</style>
