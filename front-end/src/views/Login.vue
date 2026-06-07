<template>
  <main class="login-page" :style="pageStyle">
    <div class="background-image" aria-hidden="true"></div>
    <div class="background-light" aria-hidden="true"></div>

    <button type="button" class="back-button" aria-label="返回首页">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M9 6l-6 6 6 6" />
        <path d="M21 12H4" />
      </svg>
      <span>返回首页</span>
    </button>

    <form class="login-card" aria-label="登入美育系统" @submit.prevent="handleSubmit">
      <div class="water-ripple" aria-hidden="true"></div>

      <header class="card-heading">
        <p>Meiyu System</p>
        <h1>登录</h1>
      </header>

      <label class="input-group" for="email">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect width="20" height="14" x="2" y="5" rx="2" />
          <path d="M2 7l10 7 10-7" />
        </svg>
        <span class="input-wrapper">
          <input id="email" type="email" name="email" placeholder=" " autocomplete="email" />
          <span class="floating-label">邮箱</span>
        </span>
      </label>

      <label class="input-group" for="password">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect width="14" height="10" x="5" y="11" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          <path d="M12 16v2" />
        </svg>
        <span class="input-wrapper">
          <input
            id="password"
            type="password"
            name="password"
            placeholder=" "
            autocomplete="current-password"
          />
          <span class="floating-label">密码</span>
        </span>
      </label>

      <div class="form-options">
        <label class="remember-check">
          <input type="checkbox" name="remember" />
          <span>记住我</span>
        </label>
        <button type="button">忘记密码</button>
      </div>

      <button type="submit" class="submit-button" :class="{ loading: isSubmitting }">
        <span>{{ isSubmitting ? '登入中' : '登录系统' }}</span>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M11 15l3-3-3-3" />
          <path d="M4.5 12H14" />
          <path d="M18 5v14" />
        </svg>
      </button>

      <footer class="card-footer">
        <span>还没有账号？</span>
        <button type="button">注册账号</button>
      </footer>
    </form>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import bgImage from '../assets/images/home-bg.jpg'

const isSubmitting = ref(false)

const pageStyle = computed(() => ({
  '--bg-image': `url(${bgImage})`,
}))

function handleSubmit() {
  isSubmitting.value = true
  window.setTimeout(() => {
    isSubmitting.value = false
  }, 1200)
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: grid;
  min-height: 100vh;
  place-items: center;
  overflow: hidden;
  padding: 28px;
  color: #fffaf0;
  background: #07100d;
  font-family:
    Inter,
    'PingFang SC',
    'Microsoft YaHei',
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    sans-serif;
  isolation: isolate;
}

.background-image,
.background-light {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.background-image {
  z-index: -3;
  background-image: var(--bg-image);
  background-position: center;
  background-size: cover;
  filter: saturate(1.02) contrast(1.04) brightness(0.84);
  transform: scale(1.03);
}

.background-light {
  z-index: -2;
  background:
    radial-gradient(circle at 28% 22%, rgba(255, 225, 162, 0.24), transparent 30%),
    radial-gradient(circle at 76% 64%, rgba(95, 218, 198, 0.2), transparent 26%),
    linear-gradient(115deg, rgba(3, 12, 11, 0.32), rgba(8, 13, 16, 0.1) 48%, rgba(2, 7, 8, 0.34));
}

button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

button:focus-visible,
input:focus-visible {
  outline: 2px solid rgba(255, 221, 156, 0.9);
  outline-offset: 3px;
}

svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 2;
}

.back-button {
  position: fixed;
  top: 24px;
  left: 24px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 40px;
  padding: 0 16px;
  color: rgba(255, 250, 240, 0.9);
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(18px) saturate(1.25);
  transition:
    background-color 0.24s ease,
    transform 0.24s ease;
}

.back-button:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateX(-2px);
}

.login-card {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  width: min(410px, 100%);
  gap: 20px;
  padding: 34px;
  overflow: hidden;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.26), rgba(255, 255, 255, 0.08)),
    rgba(13, 21, 23, 0.46);
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 8px;
  box-shadow:
    0 26px 72px rgba(0, 0, 0, 0.34),
    inset 0 1px 0 rgba(255, 255, 255, 0.28),
    inset 0 -1px 0 rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(28px) saturate(1.45);
}

.login-card::before {
  position: absolute;
  inset: 0;
  content: '';
  background:
    linear-gradient(115deg, rgba(255, 255, 255, 0.3), transparent 28%),
    radial-gradient(circle at 20% 10%, rgba(255, 239, 198, 0.34), transparent 26%),
    radial-gradient(circle at 85% 18%, rgba(107, 228, 205, 0.24), transparent 22%);
  opacity: 0.78;
  pointer-events: none;
}

.water-ripple {
  position: absolute;
  inset: -35%;
  background:
    repeating-radial-gradient(
      ellipse at 50% 46%,
      rgba(255, 255, 255, 0.16) 0 1px,
      transparent 1px 15px
    ),
    linear-gradient(110deg, transparent 20%, rgba(255, 255, 255, 0.24) 46%, transparent 64%);
  opacity: 0.2;
  transform: rotate(-10deg);
  animation: waterDrift 9s ease-in-out infinite alternate;
  pointer-events: none;
}

.card-heading,
.input-group,
.form-options,
.submit-button,
.card-footer {
  position: relative;
  z-index: 1;
}

.card-heading {
  display: grid;
  gap: 6px;
  text-align: center;
}

.card-heading p {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
  color: #f7ca75;
}

.card-heading h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.1;
  letter-spacing: 0;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 58px;
  padding: 0 16px;
  color: rgba(255, 250, 240, 0.72);
  background: rgba(4, 12, 13, 0.34);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  box-shadow: inset 0 1px 8px rgba(255, 255, 255, 0.05);
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease,
    box-shadow 0.25s ease,
    color 0.25s ease;
}

.input-group:focus-within {
  color: #ffe4a3;
  background: rgba(3, 10, 11, 0.46);
  border-color: rgba(247, 202, 117, 0.62);
  box-shadow:
    inset 0 1px 10px rgba(255, 255, 255, 0.08),
    0 0 28px rgba(247, 202, 117, 0.16);
}

.input-wrapper {
  position: relative;
  display: block;
  width: 100%;
  min-width: 0;
}

.input-wrapper input {
  width: 100%;
  height: 34px;
  padding: 12px 0 0;
  color: #fffaf0;
  background: transparent;
  border: 0;
  outline: 0;
}

.floating-label {
  position: absolute;
  top: 50%;
  left: 0;
  font-size: 15px;
  line-height: 1;
  color: rgba(255, 250, 240, 0.62);
  pointer-events: none;
  transform: translateY(-50%);
  transition:
    top 0.22s ease,
    color 0.22s ease,
    font-size 0.22s ease,
    transform 0.22s ease;
}

.input-wrapper input:focus + .floating-label,
.input-wrapper input:not(:placeholder-shown) + .floating-label {
  top: 2px;
  font-size: 12px;
  color: #f7ca75;
  transform: translateY(0);
}

.form-options,
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  font-size: 14px;
  color: rgba(255, 250, 240, 0.74);
}

.form-options button,
.card-footer button {
  padding: 0;
  color: #f7ca75;
  background: transparent;
  transition: color 0.22s ease;
}

.form-options button:hover,
.card-footer button:hover {
  color: #ffe1a2;
}

.remember-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.remember-check input {
  width: 15px;
  height: 15px;
  margin: 0;
  accent-color: #f7ca75;
}

.submit-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  height: 52px;
  overflow: hidden;
  color: #07100d;
  font-weight: 800;
  background: linear-gradient(90deg, #f7ca75, #f8dfac 48%, #6fdec7);
  border-radius: 8px;
  box-shadow: 0 18px 34px rgba(247, 202, 117, 0.22);
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease;
}

.submit-button::before {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(
    115deg,
    transparent 0%,
    rgba(255, 255, 255, 0.58) 45%,
    transparent 64%
  );
  transform: translateX(-115%);
  transition: transform 0.6s ease;
}

.submit-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 22px 42px rgba(247, 202, 117, 0.28);
}

.submit-button:hover::before,
.submit-button.loading::before {
  transform: translateX(115%);
}

.submit-button span,
.submit-button svg {
  position: relative;
  z-index: 1;
}

.submit-button.loading svg {
  animation: spinArrow 0.9s linear infinite;
}

@keyframes waterDrift {
  from {
    transform: translate3d(-2%, -1%, 0) rotate(-10deg);
  }

  to {
    transform: translate3d(2%, 1%, 0) rotate(-7deg);
  }
}

@keyframes spinArrow {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 520px) {
  .login-page {
    padding: 20px;
  }

  .back-button {
    top: 18px;
    left: 18px;
    width: 40px;
    padding: 0;
  }

  .back-button span {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }

  .login-card {
    padding: 26px 20px;
  }

  .form-options,
  .card-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
