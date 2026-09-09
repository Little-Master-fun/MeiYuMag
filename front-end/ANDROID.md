# 美育 Android 测试版

基于 Tauri 2，复用 Vue / Three.js 场景。前端和 3D 资源随 APK 离线打包；FastAPI、数据库、AI 审核、短信和邮件服务仍运行在服务器上，**不会把后端或 `.env` 密钥打进 App**。

## 安装与首次连接

1. 安装构建出的 ARM64 debug APK。仅用于测试，不是上架发布包；适用于 Android 7.0 / API 24 及以上的 ARM64 设备。请更新 Android System WebView / Chrome，3D 页面需要支持 WebGL 2 的设备。
2. 首次打开，在“为信件填写地址”中输入后端根地址，例如 `https://meiyu.example.edu.cn`。不需要添加 `/api/v1`。
3. 点击“测试连接”，成功后“保存并进入”，再使用该服务器上的账号登录。
4. 右下角“服务器”入口可以重新设置。更换地址会清除 App 的登录令牌并重新加载，未确认的暂存文件不会保留。

局域网测试：手机和电脑连接同一个 Wi-Fi，后端监听所有网卡：

```sh
cd back-end
conda activate fastapi
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

在电脑网络设置中找到局域网 IP，例如 `192.168.1.20`，在 App 填写 `http://192.168.1.20:8000`。确认电脑防火墙允许连接 8000 端口。手机上的 `localhost` / `127.0.0.1` 指手机自身，不能用来访问电脑（USB 调试的 `adb reverse tcp:8000 tcp:8000` 除外）。

仅 debug 版允许局域网 / 回环地址使用 HTTP；正式版本要求 HTTPS 且校验证书。HTTP 测试请使用测试账号和示例材料，不要上传真实个人敏感信息。选择服务器意味着向其发送后续登录信息与材料，请只填写可信地址。

## 网络与文件

- Android 使用 Tauri 原生 HTTP，保留注册图片验证码所需的 Cookie 会话，避免 WebView 的第三方 Cookie / CORS 限制；网页继续使用原有请求方式。
- API 请求只能发往配置的服务器，不自动跟随重定向；如服务器返回 301 / 302，请填写重定向后的最终根地址。
- 点击信封仍通过系统文件选择器选择一个或多个文件，沿用“暂存 → 删除 / 继续添加 → 确认提交”的流程。
- 示例文件和申请材料下载通过 Android 系统“另存为”选择保存位置。仅授予用户选定文件的写入权限，不申请整个存储空间的访问权限。
- 服务器设置、登录状态保存在 App 自己的数据区域；此测试版沿用网页的令牌存储方式，正式发布前应另行完成安全存储、签名和隐私合规检查。

## 构建环境

需要 Node.js（符合 package.json engines）、pnpm、Rust、JDK 17、Android SDK 与 NDK。参考 [Tauri 环境要求](https://v2.tauri.app/start/prerequisites/)。

本机已安装：

- JDK：`/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`
- SDK：`/Users/mact/Library/Android/sdk`
- SDK Platform 36、Build Tools 35.0.0 / 36.0.0、Platform Tools
- NDK：28.2.13676358
- Rust target：`aarch64-linux-android`

构建脚本会自动查找本机常见的 JDK、SDK 以及 SDK 下最新的 NDK，不修改系统 shell 配置。其他电脑可以显式设置 `JAVA_HOME`、`ANDROID_HOME`、`NDK_HOME`。

```sh
cd front-end
pnpm install --frozen-lockfile
rustup target add aarch64-linux-android
pnpm test
pnpm android:apk
```

Android 原生工程已纳入源代码，正常无需重新 init。首次生成 / 重建工程使用 `pnpm android:init`，不要覆盖自定义的原生改动。

默认 APK 输出：`src-tauri/gen/android/app/build/outputs/apk/universal/debug/app-universal-debug.apk`。当前脚本只构建 ARM64，所以即使目录名是 universal，包内也仅包含 `arm64-v8a`。调试版省略 Rust 调试符号以减小安装包，仍保留 WebView 调试能力。

USB 真机调试：开启手机开发者选项和 USB 调试，确认 `adb devices` 已授权，然后运行 `pnpm android:dev`。打包后的 APK 不依赖 Vite 开发服务器。

## 发布前

`pnpm android:release` 构建 release APK，但不代替发行签名配置。当前 debug 版使用本机 Android 调试证书，包名 `com.meiyu.venue.debug`；正式包名暂定 `com.meiyu.venue`，发布前应确认组织标识并配置自己的签名证书。不要提交 keystore 或签名密码。

参见 [Tauri Android 分发与签名](https://v2.tauri.app/distribute/google-play/)。正式发布还需要真实设备覆盖测试（首次连接、登录 / 注册、验证码、日历、3D 动画、多个文件上传、取消与下载、返回键、横竖屏、键盘、网络中断）。
