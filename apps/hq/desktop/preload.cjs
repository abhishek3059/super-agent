// The page only listens. It cannot reach HQ, the session or the file system.
const { contextBridge, ipcRenderer } = require('electron');
const channels = ['cursor', 'area', 'mode', 'companion', 'connection'];
contextBridge.exposeInMainWorld('overlay', {
  on: (fn) => { for (const c of channels) ipcRenderer.on(c, (_e, value) => fn(c, value)); },
});
