import { onBeforeUnmount, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

interface PortalAuthOptions {
  onAuthenticated: () => void
}

export function usePortalAuth({ onAuthenticated }: PortalAuthOptions) {
  const auth = useAuthStore()
  const authFormStage = ref<HTMLDivElement | null>(null)
  const loginPanelVisible = ref(false)
  const loginSucceeded = ref(false)
  const account = ref('')
  const password = ref('')
  const passwordVisible = ref(false)
  const authMode = ref<'login' | 'register'>('login')
  const registerEmail = ref('')
  const registerOrganization = ref('')
  const registerMobile = ref('')
  const registerImageCode = ref('')
  const registerSmsCode = ref('')
  const registerPassword = ref('')
  const registerPasswordConfirm = ref('')
  const registerPasswordVisible = ref(false)
  const registrationCaptchaUrl = ref('')
  const captchaLoading = ref(false)
  const smsSending = ref(false)
  const smsSent = ref(false)
  const smsCountdown = ref(0)
  const formError = ref('')
  const formNotice = ref('')
  let smsCountdownTimer: ReturnType<typeof setInterval> | null = null

  function stopSmsCountdown() {
    if (smsCountdownTimer) clearInterval(smsCountdownTimer)
    smsCountdownTimer = null
    smsCountdown.value = 0
  }

  function startSmsCountdown() {
    stopSmsCountdown()
    smsCountdown.value = 60
    smsCountdownTimer = setInterval(() => {
      smsCountdown.value -= 1
      if (smsCountdown.value <= 0) stopSmsCountdown()
    }, 1000)
  }

  function revokeRegistrationCaptcha() {
    if (!registrationCaptchaUrl.value) return
    URL.revokeObjectURL(registrationCaptchaUrl.value)
    registrationCaptchaUrl.value = ''
  }

  async function loadRegistrationCaptcha() {
    captchaLoading.value = true
    formError.value = ''
    formNotice.value = ''
    smsSent.value = false
    stopSmsCountdown()

    const captcha = await auth.requestRegistrationCaptcha()
    revokeRegistrationCaptcha()
    if (captcha) registrationCaptchaUrl.value = URL.createObjectURL(captcha)
    else formError.value = auth.error || '图片验证码加载失败，请稍后重试'
    captchaLoading.value = false
  }

  function changeAuthMode(mode: 'login' | 'register') {
    if (authMode.value === mode) return
    authMode.value = mode
    formError.value = ''
    formNotice.value = ''
    loginSucceeded.value = false
    if (mode === 'register' && !registrationCaptchaUrl.value) {
      void loadRegistrationCaptcha()
    }
  }

  function handleAuthFormBeforeLeave(element: Element) {
    if (!authFormStage.value) return
    authFormStage.value.style.height = `${(element as HTMLElement).offsetHeight}px`
  }

  function handleAuthFormBeforeEnter(element: Element) {
    const stage = authFormStage.value
    if (!stage) return
    const nextForm = element as HTMLElement
    void stage.offsetHeight
    requestAnimationFrame(() => {
      stage.style.height = `${nextForm.scrollHeight}px`
    })
  }

  function handleAuthFormAfterEnter() {
    if (authFormStage.value) authFormStage.value.style.height = 'auto'
  }

  function invalidateSmsVerification() {
    if (!smsSent.value) return
    smsSent.value = false
    formNotice.value = '手机号或图片验证码已修改，请重新获取短信验证码。'
    stopSmsCountdown()
  }

  async function handleLogin() {
    if (!account.value.trim() || !password.value) {
      formError.value = '请输入邮箱或手机号及密码'
      return
    }

    formError.value = ''
    loginSucceeded.value = false
    const success = await auth.login(account.value.trim(), password.value)
    if (success) {
      loginSucceeded.value = true
      onAuthenticated()
      return
    }
    formError.value = auth.error || '登录失败，请检查账号和密码'
  }

  async function handleSendRegistrationSms() {
    if (!/^\d{11}$/.test(registerMobile.value)) {
      formError.value = '请输入11位手机号'
      return
    }
    if (!/^\d{4}$/.test(registerImageCode.value)) {
      formError.value = '请输入图片中的4位验证码'
      return
    }

    smsSending.value = true
    formError.value = ''
    formNotice.value = ''
    const success = await auth.sendRegistrationSms(registerMobile.value, registerImageCode.value)
    smsSending.value = false

    if (success) {
      smsSent.value = true
      formNotice.value = '短信验证码已发送，请在两分钟内完成注册。'
      startSmsCountdown()
      return
    }

    const errorMessage = auth.error || '短信验证码发送失败'
    await loadRegistrationCaptcha()
    formError.value = errorMessage
  }

  async function handleRegister() {
    const email = registerEmail.value.trim()
    const organization = registerOrganization.value.trim()
    if (!email || !organization) {
      formError.value = '请填写邮箱和所属组织'
      return
    }
    if (!/^\d{11}$/.test(registerMobile.value)) {
      formError.value = '请输入11位手机号'
      return
    }
    if (!smsSent.value || !/^\d{6}$/.test(registerSmsCode.value)) {
      formError.value = '请先完成手机验证并输入6位短信验证码'
      return
    }
    if (registerPassword.value.length < 8) {
      formError.value = '密码至少需要8个字符'
      return
    }
    if (registerPassword.value !== registerPasswordConfirm.value) {
      formError.value = '两次输入的密码不一致'
      return
    }

    formError.value = ''
    formNotice.value = ''
    loginSucceeded.value = false
    const success = await auth.register(
      email,
      registerPassword.value,
      organization,
      registerMobile.value,
      registerSmsCode.value,
    )

    if (success) {
      loginSucceeded.value = true
      stopSmsCountdown()
      onAuthenticated()
      return
    }

    const errorMessage = auth.error || '注册失败，请检查认证信息'
    registerSmsCode.value = ''
    smsSent.value = false
    await loadRegistrationCaptcha()
    formError.value = errorMessage
  }

  onBeforeUnmount(() => {
    stopSmsCountdown()
    revokeRegistrationCaptcha()
  })

  return {
    account,
    auth,
    authFormStage,
    authMode,
    captchaLoading,
    changeAuthMode,
    formError,
    formNotice,
    handleAuthFormAfterEnter,
    handleAuthFormBeforeEnter,
    handleAuthFormBeforeLeave,
    handleLogin,
    handleRegister,
    handleSendRegistrationSms,
    invalidateSmsVerification,
    loadRegistrationCaptcha,
    loginPanelVisible,
    loginSucceeded,
    password,
    passwordVisible,
    registerEmail,
    registerImageCode,
    registerMobile,
    registerOrganization,
    registerPassword,
    registerPasswordConfirm,
    registerPasswordVisible,
    registerSmsCode,
    registrationCaptchaUrl,
    smsCountdown,
    smsSending,
    smsSent,
  }
}
