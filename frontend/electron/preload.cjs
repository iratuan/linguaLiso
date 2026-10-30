// Ponte mínima entre o renderer e o processo principal. Não expõe Node nem IPC genérico.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("englishTeacher", {
  platform: process.platform,
  appVersion: process.env.npm_package_version || "0.1.0",
  // Janela flutuante do professor (sempre no topo). Só estes dois comandos.
  chat: {
    popout: () => ipcRenderer.invoke("chat:popout"),
    restore: () => ipcRenderer.invoke("chat:restore"),
  },
});
