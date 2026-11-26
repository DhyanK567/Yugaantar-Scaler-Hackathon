const { contextBridge, ipcRenderer } = require("electron");

const apiPortArg = process.argv.find((a) => a.startsWith("--medilocker-api-port="));
const apiPort = apiPortArg ? apiPortArg.split("=")[1] : "8000";

contextBridge.exposeInMainWorld("medilockerDesktop", {
  isDesktop: true,
  apiBase: `http://127.0.0.1:${apiPort}`,
  platform: process.platform,
  openFilesDialog: () => ipcRenderer.invoke("dialog:openFiles"),
  saveFileDialog: (defaultName) => ipcRenderer.invoke("dialog:saveFile", defaultName),
  getAppInfo: () => ipcRenderer.invoke("app:info"),
});
