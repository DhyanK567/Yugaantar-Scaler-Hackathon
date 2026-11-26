const { app, BrowserWindow, Menu, dialog, ipcMain, session } = require("electron");
const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");
const { spawn, execFileSync } = require("child_process");

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
  process.exit(0);
}

let mainWindow = null;
let backendProc = null;
let frontendProc = null;
let isShuttingDown = false;
let activeApiPort = 8000;
let activeUiPort = 3001;

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const addr = srv.address();
      const port = typeof addr === "object" && addr ? addr.port : 0;
      srv.close(() => resolve(port));
    });
  });
}

function waitForHttp(url, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode >= 200 && res.statusCode < 500) {
          resolve(true);
        } else if (Date.now() - start > timeoutMs) {
          reject(new Error(`Timeout waiting for ${url} (status ${res.statusCode})`));
        } else {
          setTimeout(check, 350);
        }
      });
      req.on("error", () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Timeout waiting for ${url}`));
        } else {
          setTimeout(check, 350);
        }
      });
      req.setTimeout(1500, () => req.destroy());
    };
    check();
  });
}

function ensureUserSecrets(userDataDir) {
  const dataDir = path.join(userDataDir, "data");
  fs.mkdirSync(dataDir, { recursive: true });
  const secretsPath = path.join(userDataDir, "secrets.json");
  if (fs.existsSync(secretsPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(secretsPath, "utf-8"));
      if (parsed.rakshaSecret && parsed.authSecret) return { ...parsed, dataDir };
    } catch {
      // regenerate if corrupt
    }
  }
  const secrets = {
    rakshaSecret: crypto.randomBytes(32).toString("hex"),
    authSecret: crypto.randomBytes(32).toString("hex"),
  };
  fs.writeFileSync(secretsPath, JSON.stringify(secrets, null, 2), { mode: 0o600 });
  return { ...secrets, dataDir };
}

function loadWindowState(userDataDir) {
  const statePath = path.join(userDataDir, "window-state.json");
  try {
    if (fs.existsSync(statePath)) {
      const s = JSON.parse(fs.readFileSync(statePath, "utf-8"));
      if (s.width >= 960 && s.height >= 640) return s;
    }
  } catch {
    // ignore
  }
  return { width: 1366, height: 840 };
}

function saveWindowState(userDataDir, win) {
  if (!win || win.isDestroyed()) return;
  try {
    const bounds = win.getBounds();
    fs.writeFileSync(path.join(userDataDir, "window-state.json"), JSON.stringify(bounds));
  } catch {
    // ignore
  }
}

function killProcessTree(proc) {
  if (!proc || proc.killed || !proc.pid) return;
  try {
    if (process.platform === "win32") {
      execFileSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      proc.kill("SIGTERM");
    }
  } catch {
    // ignore already exited
  }
}

function shutdownServices() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  killProcessTree(frontendProc);
  killProcessTree(backendProc);
  frontendProc = null;
  backendProc = null;
}

function resolveRuntimePaths() {
  if (app.isPackaged) {
    const res = process.resourcesPath;
    return {
      backendExe: path.join(res, "backend", "medilocker-backend.exe"),
      nodeExe: path.join(res, "node", "node.exe"),
      webServerJs: path.join(res, "web", "server.js"),
      webCwd: path.join(res, "web"),
      iconPath: path.join(res, "..", "resources", "app.asar", "assets", "icon.ico"),
    };
  }
  const repoRoot = path.resolve(__dirname, "..");
  return {
    backendExe: path.join(__dirname, "py_dist", "medilocker-backend", "medilocker-backend.exe"),
    nodeExe: process.execPath.endsWith("node.exe") ? process.execPath : "node",
    webServerJs: path.join(__dirname, "web_dist", "server.js"),
    webCwd: path.join(__dirname, "web_dist"),
    iconPath: path.join(__dirname, "assets", "icon.ico"),
    repoRoot,
  };
}

function buildAppMenu() {
  const template = [
    {
      label: "File",
      submenu: [
        { role: "reload" },
        { type: "separator" },
        { role: "quit", label: "Exit MediLocker" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "About MediLocker",
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: "info",
              title: "About MediLocker",
              message: `MediLocker v${app.getVersion()}`,
              detail:
                "Offline-First Healthcare Data Privacy Infrastructure.\n" +
                "CPU-only · Zero LLMs · Local Loopback Execution (127.0.0.1)\n\n" +
                `API Port: 127.0.0.1:${activeApiPort}\n` +
                `UI Port: 127.0.0.1:${activeUiPort}\n` +
                `Data Directory: ${path.join(app.getPath("userData"), "data")}`,
            });
          },
        },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function startDesktopApp() {
  const userDataDir = app.getPath("userData");
  const { rakshaSecret, authSecret, dataDir } = ensureUserSecrets(userDataDir);
  const paths = resolveRuntimePaths();

  activeApiPort = await getFreePort();
  activeUiPort = await getFreePort();

  const sharedEnv = {
    ...process.env,
    MEDILOCKER_DATA_DIR: dataDir,
    MEDILOCKER_OFFLINE_MODE: "true",
    MEDILOCKER_ENV: "development",
    RAKSHA_SECRET: rakshaSecret,
    MEDILOCKER_AUTH_SECRET: authSecret,
    HF_HUB_OFFLINE: "1",
    TRANSFORMERS_OFFLINE: "1",
    FRONTEND_ORIGINS: `http://127.0.0.1:${activeUiPort},http://localhost:${activeUiPort}`,
  };

  let backendStderr = "";
  if (!fs.existsSync(paths.backendExe)) {
    throw new Error(`Bundled backend executable not found at: ${paths.backendExe}`);
  }
  backendProc = spawn(
    paths.backendExe,
    ["--host", "127.0.0.1", "--port", String(activeApiPort)],
    { env: sharedEnv, windowsHide: true, stdio: ["ignore", "ignore", "pipe"] }
  );
  backendProc.stderr.on("data", (chunk) => {
    if (backendStderr.length < 2000) backendStderr += chunk.toString("utf-8");
  });
  backendProc.on("exit", (code) => {
    if (!isShuttingDown && code !== 0) {
      dialog.showErrorBox(
        "MediLocker Backend Stopped",
        `Local privacy backend exited unexpectedly (code ${code}).`
      );
      app.quit();
    }
  });

  try {
    await waitForHttp(`http://127.0.0.1:${activeApiPort}/api/health`, 30000);
  } catch (err) {
    throw new Error(
      `Backend health check failed on 127.0.0.1:${activeApiPort}.\n${backendStderr.slice(0, 400)}`
    );
  }

  if (!fs.existsSync(paths.webServerJs)) {
    throw new Error(`Bundled Next.js server not found at: ${paths.webServerJs}`);
  }
  frontendProc = spawn(paths.nodeExe, [paths.webServerJs], {
    cwd: paths.webCwd,
    env: {
      ...sharedEnv,
      HOSTNAME: "127.0.0.1",
      PORT: String(activeUiPort),
    },
    windowsHide: true,
    stdio: "ignore",
  });

  await waitForHttp(`http://127.0.0.1:${activeUiPort}/login`, 30000);

  // Strict Content Security Policy & Loopback-only guard
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const csp = [
      "default-src 'self'",
      `connect-src 'self' http://127.0.0.1:${activeApiPort} http://127.0.0.1:${activeUiPort}`,
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      "frame-ancestors 'none'",
    ].join("; ");
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [csp],
      },
    });
  });

  const winState = loadWindowState(userDataDir);
  mainWindow = new BrowserWindow({
    width: winState.width,
    height: winState.height,
    x: winState.x,
    y: winState.y,
    minWidth: 960,
    minHeight: 640,
    title: "MediLocker",
    icon: path.join(__dirname, "assets", "icon.ico"),
    backgroundColor: "#F4F4F2",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      additionalArguments: [`--medilocker-api-port=${activeApiPort}`],
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // Restrict navigation to local MediLocker UI only
  const allowedOrigin = `http://127.0.0.1:${activeUiPort}`;
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(allowedOrigin)) {
      event.preventDefault();
    }
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(allowedOrigin)) return { action: "allow" };
    return { action: "deny" };
  });

  mainWindow.on("close", () => saveWindowState(userDataDir, mainWindow));
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  buildAppMenu();
  await mainWindow.loadURL(`${allowedOrigin}/login`);
}

// Explicit, validated IPC handlers
ipcMain.handle("dialog:openFiles", async () => {
  if (!mainWindow) return [];
  const res = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Healthcare Datasets", extensions: ["csv", "tsv", "json", "jsonl", "txt", "pdf", "png"] },
    ],
  });
  return res.canceled ? [] : res.filePaths;
});

ipcMain.handle("dialog:saveFile", async (_event, defaultName) => {
  if (!mainWindow || typeof defaultName !== "string") return null;
  const safeName = path.basename(defaultName);
  const res = await dialog.showSaveDialog(mainWindow, { defaultPath: safeName });
  return res.canceled ? null : res.filePath;
});

ipcMain.handle("app:info", () => ({
  version: app.getVersion(),
  apiPort: activeApiPort,
  uiPort: activeUiPort,
  dataDir: path.join(app.getPath("userData"), "data"),
}));

app.on("second-instance", () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
});

app.whenReady().then(async () => {
  try {
    await startDesktopApp();
  } catch (err) {
    dialog.showErrorBox("MediLocker Startup Error", String(err && err.message ? err.message : err));
    shutdownServices();
    app.quit();
  }
});

app.on("before-quit", () => shutdownServices());
app.on("window-all-closed", () => {
  shutdownServices();
  app.quit();
});
