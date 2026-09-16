<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import house from '@/assets/images/forest-house-loading.webp'
import { advanceInkProgress, inkFinishDelay, inkRadius, inkSeeds, inkTarget } from '../inkLoading'

const props = defineProps<{ progress: number; ready: boolean; error?: string }>()
const emit = defineEmits<{ 'before-reveal': []; complete: [] }>()
const id = `ink-${useId().replace(/[^a-zA-Z0-9-]/g, '')}`
const shown = ref(0), leaving = ref(false), artReady = ref(false), artFailed = ref(false)
const reduced = ref(false)
const percent = computed(() => Math.floor(shown.value))
const target = computed(() => inkTarget(props.progress, props.ready))
const stage = computed(() => props.error ? '这一页暂未展开' : shown.value >= 100 ? '小屋已就绪' :
  shown.value >= 85 ? '等一阵风，走进林间' : shown.value >= 55 ? '为林间添一点颜色' :
    shown.value >= 25 ? '屋檐在纸上慢慢浮现' : '第一滴墨，落在林间')
let frame = 0, previous = 0, done = false
let startedAt = 0
let finishTimer: ReturnType<typeof setTimeout> | undefined
let fadeTimer: ReturnType<typeof setTimeout> | undefined
let media: MediaQueryList | undefined

function finish() {
  if (done || props.error || !props.ready || shown.value < 100 || !artReady.value) return
  done = true
  finishTimer = setTimeout(() => {
    // The parent sets the real camera, scale and renders synchronously while
    // this cover is opaque. Yield a frame before exposing the canvas.
    emit('before-reveal')
    frame = requestAnimationFrame(() => {
      frame = 0
      if (props.error) return
      leaving.value = true
      fadeTimer = setTimeout(() => emit('complete'), reduced.value ? 0 : 600)
    })
  }, inkFinishDelay(performance.now() - startedAt, reduced.value))
}
function tick(now: number) {
  frame = 0
  if (props.error) return
  const elapsed = previous ? now - previous : 32
  if (elapsed < 32 && !reduced.value) { frame = requestAnimationFrame(tick); return }
  previous = now
  shown.value = advanceInkProgress(shown.value, target.value, elapsed, reduced.value)
  if (shown.value < target.value) frame = requestAnimationFrame(tick)
  else { previous = 0; finish() }
}
function schedule() {
  if (startedAt && !frame && !done && !props.error) frame = requestAnimationFrame(tick)
}
function updateMotion() { reduced.value = media?.matches ?? false; schedule() }
function retry() { window.location.reload() }
watch([target, artReady], schedule)
watch(() => props.error, error => {
  if (!error) return
  cancelAnimationFrame(frame); frame = 0
  clearTimeout(finishTimer); clearTimeout(fadeTimer)
  leaving.value = false
})
onMounted(() => {
  media = window.matchMedia('(prefers-reduced-motion: reduce)')
  media.addEventListener('change', updateMotion)
  // Start the minimum display duration from the first painted frame, rather
  // than setup time that may be spent blocked on WebGL initialization.
  frame = requestAnimationFrame(() => { frame = 0; startedAt = performance.now(); updateMotion() })
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame); clearTimeout(finishTimer); clearTimeout(fadeTimer)
  media?.removeEventListener('change', updateMotion)
})
</script>

<template>
  <section class="ink-loader" :class="{ 'is-leaving': leaving, 'is-error': error }" aria-label="正在准备美育小屋" :aria-busy="!error && !leaving">
    <div class="ink-loader-brand"><span class="brand-mark">美育</span><span>MEIYU · A PLACE TO GATHER</span></div>
    <div class="ink-loader-center">
      <div class="ink-art" aria-hidden="true">
        <svg viewBox="0 0 560 476" class="ink-picture">
          <defs>
            <filter :id="`${id}-bleed`" filterUnits="userSpaceOnUse" x="0" y="0" width="560" height="476" color-interpolation-filters="sRGB">
              <feTurbulence type="fractalNoise" baseFrequency=".038 .055" numOctaves="2" seed="12" result="grain" />
              <feColorMatrix in="grain" type="matrix" values="4 0 0 0 -1.5  0 4 0 0 -1.5  0 0 4 0 -1.5  0 0 0 1 0" result="ink-grain" />
              <feDisplacementMap in="SourceGraphic" in2="ink-grain" scale="20" xChannelSelector="R" yChannelSelector="G" />
              <feGaussianBlur stdDeviation=".65" />
            </filter>
            <mask :id="`${id}-reveal`" maskUnits="userSpaceOnUse" x="0" y="0" width="560" height="476" style="mask-type: alpha">
              <g fill="white" :filter="`url(#${id}-bleed)`">
                <ellipse v-for="([x, y, start], i) in inkSeeds" :key="i" :cx="x" :cy="y" :rx="inkRadius(shown, start)" :ry="inkRadius(shown, start) * (.74 + (i % 3) * .13)" />
              </g>
            </mask>
          </defs>
          <image :href="house" width="560" height="476" opacity=".045" class="house-ghost" />
          <image v-if="!artFailed" :href="house" width="560" height="476" :mask="shown >= 100 ? undefined : `url(#${id}-reveal)`" @load="artReady = true" @error="artFailed = artReady = true" />
          <g v-else fill="none" stroke="currentColor" stroke-width="2" :opacity="shown / 100">
            <path d="M175 290V210L280 125 385 210V290ZM155 213 280 108 405 213M252 290V229H304V290M198 230H231V255H198ZM329 230H362V255H329Z" />
          </g>
        </svg>
        <span class="art-caption">林间 · 美育小屋</span>
      </div>
      <div class="ink-copy">
        <p class="ink-eyebrow">一纸之间，林间相见</p>
        <h1>{{ stage }}</h1>
        <div v-if="!error" class="ink-progress" role="progressbar" aria-label="场景加载进度" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
          <span class="ink-milestones" aria-hidden="true"><i v-for="n in 4" :key="n" :class="{ filled: shown >= n * 25 }" /></span>
          <span class="ink-progress-label">{{ shown >= 100 ? '显影完成' : '正在显影' }}</span>
          <span class="ink-counter">{{ String(percent).padStart(3, '0') }}<small> / 100</small></span>
        </div>
        <template v-else><p class="ink-error" role="alert">{{ error }}</p><button class="ink-retry" @click="retry">重新展开 <span aria-hidden="true">↗</span></button></template>
      </div>
    </div>
    <p class="ink-footer">让每一次相聚，都有一处好风景</p>
  </section>
</template>

<style scoped>
.ink-loader { position: absolute; inset: 0; z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: space-between; overflow: hidden; padding: clamp(24px, 5vh, 54px) 24px 26px; box-sizing: border-box; color: #526551; background: #f5ecd9; opacity: 1; transition: opacity 600ms ease; }
.ink-loader::before { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: .085; background-image: radial-gradient(#aa9573 0.5px, transparent .6px), radial-gradient(#ad9777 .5px, transparent .6px); background-size: 5px 7px, 11px 13px; background-position: 0 0, 3px 5px; }
.ink-loader::after { content: ''; position: absolute; inset: 14px; border: 1px solid #8a98751a; pointer-events: none; }
.ink-loader.is-leaving { opacity: 0; pointer-events: none; }
.ink-loader-brand { display: flex; align-items: center; gap: 15px; font-size: 9px; letter-spacing: .25em; color: #7f8970; z-index: 1; }
.brand-mark { border: 1px solid #74846677; padding: 6px 5px; font: 16px/1.2 'STKaiti', 'KaiTi', serif; letter-spacing: .1em; writing-mode: vertical-rl; border-radius: 2px 1px 3px 1px; }
.ink-loader-center { width: min(100%, 540px); margin: auto; position: relative; text-align: center; }
.ink-art { position: relative; width: min(100%, 500px); margin: -25px auto -13px; }
.ink-picture { display: block; width: 100%; max-height: 53svh; overflow: visible; }
.art-caption { position: absolute; right: 3%; top: 49%; writing-mode: vertical-rl; font-size: 10px; letter-spacing: .28em; color: #8d927a; }
.ink-copy { position: relative; margin-top: 8px; }
.ink-eyebrow { margin: 0 0 12px; font-size: 10px; letter-spacing: .32em; color: #9a9078; }
.ink-copy h1 { font: 400 clamp(20px, 2.4vw, 26px)/1.5 'STKaiti', 'KaiTi', 'Songti SC', serif; letter-spacing: .1em; margin: 0; color: #52614e; }
.ink-progress { width: min(264px, 90%); display: flex; align-items: center; gap: 10px; margin: 24px auto 0; padding-top: 15px; border-top: 1px solid #8d947629; }
.ink-milestones { display: flex; align-items: center; gap: 6px; }
.ink-milestones i { display: block; width: 5px; height: 5px; border: 1px solid #83917477; border-radius: 42% 58% 47% 53%; transition: background .3s; transform: rotate(-20deg); }
.ink-milestones .filled { background: #6e8061; border-color: #6e8061; }
.ink-progress-label { font-size: 10px; letter-spacing: .13em; color: #8a8c74; }
.ink-counter { margin-left: auto; font: 13px/1.4 ui-monospace, monospace; color: #64735a; font-variant-numeric: tabular-nums; }
.ink-counter small { font-size: 9px; color: #9f9d86; }
.ink-footer { position: relative; margin: 20px 0 0; color: #9a9b83; letter-spacing: .2em; font-size: 10px; }
.ink-error { max-width: 300px; margin: 16px auto 0; color: #986b51; font-size: 12px; line-height: 1.8; }
.ink-retry { background: none; border: 0; border-bottom: 1px solid #8d947666; padding: 10px 6px; margin-top: 12px; font: inherit; color: #526551; cursor: pointer; }
.ink-retry:hover, .ink-retry:focus-visible { color: #8e633f; border-color: currentColor; }
@media (max-width: 600px) { .ink-art { margin-top: 0; margin-bottom: 4px; } .art-caption { right: 0; font-size: 9px; } .ink-loader-brand { font-size: 8px; } .ink-copy h1 { font-size: 21px; } .ink-footer { font-size: 9px; } }
@media (max-height: 540px) and (orientation: landscape) { .ink-loader { padding: 18px 30px; } .ink-loader-brand .brand-mark { writing-mode: horizontal-tb; } .ink-loader-center { display: flex; width: min(90%, 720px); align-items: center; gap: 28px; } .ink-art { width: 46%; margin: 0; } .ink-picture { max-height: 64svh; } .ink-copy { flex: 1; } .ink-copy h1 { font-size: 20px; } .ink-footer { margin-top: 0; } }
@media (prefers-reduced-motion: reduce) { .ink-loader, .ink-milestones i { transition: none; } }
</style>
