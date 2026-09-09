// Run locally once. Only the resulting private files travel over SSH; never
// copy .env into a build context or print credentials to the terminal.
import { readFileSync, mkdirSync, writeFileSync, chmodSync } from 'node:fs'
import { parseEnv } from 'node:util'
import { randomBytes } from 'node:crypto'
import { resolve } from 'node:path'

const output = resolve('artifacts/production-secrets')
const source = parseEnv(readFileSync('back-end/.env', 'utf8'))
mkdirSync(output, { recursive: true, mode: 0o700 })
chmodSync(output, 0o700)
const dbPassword = randomBytes(32).toString('hex')
const adminPassword = randomBytes(24).toString('base64url')
const env = {
  APP_ENV: 'production',
  DATABASE_URL: `postgresql+asyncpg://meiyu:${dbPassword}@db:5432/meiyu_system`,
  JWT_SECRET_KEY: randomBytes(48).toString('hex'),
  ACCESS_TOKEN_EXPIRE_MINUTES: '30', REFRESH_TOKEN_EXPIRE_DAYS: '7',
  UPLOAD_DIR: '/app/uploads', MAX_UPLOAD_SIZE_MB: '30',
  CORS_ORIGIN_CSV: 'https://mymag.littlemaster.fun,http://tauri.localhost,https://tauri.localhost,tauri://localhost',
  INITIAL_ADMIN_ACCOUNT: 'admin@mymag.littlemaster.fun',
  INITIAL_ADMIN_PASSWORD: adminPassword,
}
for (const key of ['SMTP_HOST', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'SMTP_FROM',
  'ADMIN_NOTIFICATION_EMAIL_CSV', 'AI_API_BASE_URL', 'AI_API_KEY', 'AI_MODEL', 'AI_TIMEOUT_SECONDS',
  'SDU_AUTH_BASE_URL', 'SDU_SERVICE_URL']) {
  if (source[key]) env[key] = source[key]
}
env.SMTP_PORT = '465'
env.SMTP_SECURITY = 'ssl'
const text = Object.entries(env).map(([key, value]) => `${key}=${JSON.stringify(value)}`).join('\n') + '\n'
writeFileSync(`${output}/backend.env`, text, { mode: 0o600, flag: 'wx' })
writeFileSync(`${output}/db_password`, dbPassword, { mode: 0o600, flag: 'wx' })
writeFileSync(`${output}/administrator.txt`, `网站：https://mymag.littlemaster.fun\n账号：${env.INITIAL_ADMIN_ACCOUNT}\n密码：${adminPassword}\n请保存在密码管理器中，不要上传至 Git。\n`, { mode: 0o600, flag: 'wx' })
console.log('Private production credentials created under artifacts/production-secrets (not printed).')
