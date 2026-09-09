import { existsSync, readdirSync } from 'node:fs'
import { homedir, platform } from 'node:os'
import { join, delimiter } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const env = { ...process.env }
env.JAVA_HOME ||= [
  '/Applications/Android Studio.app/Contents/jbr/Contents/Home',
  '/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home',
  '/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home',
].find(existsSync)
env.ANDROID_HOME ||= env.ANDROID_SDK_ROOT || (platform() === 'darwin'
  ? join(homedir(), 'Library/Android/sdk') : join(homedir(), 'Android/Sdk'))
const ndks = join(env.ANDROID_HOME, 'ndk')
if (!env.NDK_HOME && existsSync(ndks)) {
  const version = readdirSync(ndks).filter(name => /^\d/.test(name))
    .sort((a, b) => b.localeCompare(a, undefined, { numeric: true }))[0]
  if (version) env.NDK_HOME = join(ndks, version)
}
for (const key of ['JAVA_HOME', 'ANDROID_HOME', 'NDK_HOME']) {
  if (!env[key] || !existsSync(env[key])) {
    console.error(`缺少 ${key}。请先按照 ANDROID.md 安装 Android 构建环境。`)
    process.exit(1)
  }
}
env.PATH = [join(env.JAVA_HOME, 'bin'), join(env.ANDROID_HOME, 'platform-tools'), env.PATH].join(delimiter)
const cli = fileURLToPath(new URL('../node_modules/@tauri-apps/cli/tauri.js', import.meta.url))
const result = spawnSync(process.execPath, [cli, 'android', ...process.argv.slice(2)], {
  cwd: fileURLToPath(new URL('..', import.meta.url)), env, stdio: 'inherit',
})
if (result.error) console.error(result.error.message)
process.exit(result.status ?? 1)
