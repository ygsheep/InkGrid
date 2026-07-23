/**
 * 预加载脚本。
 *
 * 目前没有暴露任何 Node 能力到渲染层(contextIsolation=true, nodeIntegration=false)。
 * 后续如需桌面特有功能(如本地文件、系统通知、托盘菜单),
 * 通过 contextBridge.exposeInMainWorld 在这里白名单暴露。
 */

const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true,
});
