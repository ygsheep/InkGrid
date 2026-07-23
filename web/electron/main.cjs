/**
 * Electron 主进程
 *
 * 工作方式:
 *  - dev  (ELECTRON_DEV=1): spawn `next dev`,        等就绪后加载 http://localhost:3000
 *  - prod                  : spawn `next start -p <PORT>`, 加载 http://localhost:<PORT>
 *
 * 退出时强制 kill 子进程(Windows 用 taskkill /T 避免僵尸进程)。
 * Next.js 代码零改动,SSR/ISR/API 路由全部保留。
 */

const { app, BrowserWindow, shell } = require('electron');
const { spawn } = require('node:child_process');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');

// 子进程句柄,退出时清理
let nextProc = null;

// 模式判断
const isDev = !!process.env.ELECTRON_DEV;

// 端口:dev 用 3000(Next 默认),prod 用 3456 避免与开发模式冲突
const PORT = isDev ? 3000 : Number(process.env.PORT) || 3456;
const URL = `http://localhost:${PORT}`;

/**
 * 解析 .env.electron 文件并写入 process.env。
 *
 * 为什么需要这个:
 *  - NEXT_PUBLIC_* 变量在 `next build` 时已被内联到客户端 bundle,运行时无需再设
 *  - 但服务端变量(如 REVALIDATE_SECRET)在 `next start` 运行时读取 process.env,
 *    打包后用户双击运行没有 npm 脚本注入,所以主进程在 spawn next 之前加载此文件
 *
 * 仅 prod 模式加载(dev 模式由 npm 脚本通过 cross-env 注入)。
 */
function loadEnvFile() {
  if (isDev) return;
  const envPath = path.resolve(__dirname, '..', '.env.electron');
  if (!fs.existsSync(envPath)) return;
  const content = fs.readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx < 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    let value = trimmed.slice(eqIdx + 1).trim();
    // 去掉两端引号
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    // 不覆盖已存在的 env(允许系统环境变量优先)
    if (!process.env[key]) {
      process.env[key] = value;
    }
  }
}

loadEnvFile();

/**
 * 启动 Next.js 子进程。
 * cwd 必须是 web/ 目录(包含 package.json 与 .next)。
 */
function startNext() {
  const cwd = path.resolve(__dirname, '..');
  const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx';
  const args = isDev
    ? ['next', 'dev', '-p', String(PORT)]
    : ['next', 'start', '-p', String(PORT)];

  nextProc = spawn(cmd, args, {
    cwd,
    env: { ...process.env, PORT: String(PORT) },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });

  // 转发子进程日志到主进程控制台(打包后写入日志文件)
  nextProc.stdout.on('data', (d) => process.stdout.write(`[next] ${d}`));
  nextProc.stderr.on('data', (d) => process.stderr.write(`[next] ${d}`));

  nextProc.on('exit', (code) => {
    console.log(`[next] exited with code ${code}`);
    nextProc = null;
  });
}

/**
 * 轮询等待 Next.js 服务就绪(dev 启动较慢,prod 通常 <1s)。
 * @param {number} timeout 超时毫秒
 */
function waitForNext(timeout = 60000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(URL, (res) => {
        // 任何 HTTP 响应都说明服务已起来(包括 404)
        res.resume();
        resolve();
      });
      req.on('error', () => {
        if (Date.now() - start > timeout) {
          reject(new Error(`Next.js 启动超时(${timeout}ms)`));
        } else {
          setTimeout(check, 300);
        }
      });
      req.setTimeout(1000, () => req.destroy());
    };
    check();
  });
}

/**
 * 创建主窗口。
 */
function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 720,
    backgroundColor: '#0d1117', // 与 Obsidian Spatial 风格背景一致,避免白屏闪烁
    title: process.env.NEXT_PUBLIC_SITE_NAME || 'inkgrid.dev',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 外链默认用系统浏览器打开,不在应用内跳转
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http://localhost') || url.startsWith('http://127.0.0.1')) {
      return { action: 'allow' };
    }
    shell.openExternal(url);
    return { action: 'deny' };
  });

  win.loadURL(URL);

  if (isDev) {
    win.webContents.openDevTools({ mode: 'detach' });
  }

  return win;
}

// 单实例锁,避免多开
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const wins = BrowserWindow.getAllWindows();
    if (wins[0]) {
      if (wins[0].isMinimized()) wins[0].restore();
      wins[0].focus();
    }
  });

  app.whenReady().then(async () => {
    startNext();
    try {
      await waitForNext();
    } catch (e) {
      console.error(e.message);
      app.quit();
      return;
    }
    createWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  });
}

/**
 * 清理 Next.js 子进程。
 * Windows 下 spawn 的子进程默认是父进程的孙子,需要 taskkill /T 才能彻底结束。
 */
function killNext() {
  if (!nextProc) return;
  try {
    if (process.platform === 'win32') {
      // /T 杀进程树,/F 强制
      spawn('taskkill', ['/PID', String(nextProc.pid), '/T', '/F'], {
        windowsHide: true,
      });
    } else {
      nextProc.kill('SIGTERM');
    }
  } catch (e) {
    console.error('kill next failed:', e);
  }
  nextProc = null;
}

app.on('before-quit', killNext);
app.on('window-all-closed', () => {
  // 桌面应用统一退出(macOS 也直接退,不留在 Dock)
  app.quit();
});
