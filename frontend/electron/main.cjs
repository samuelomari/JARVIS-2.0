const { app, BrowserWindow, dialog, Menu, nativeImage, session, shell, Tray } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

let backendProcess;
let localServer;
let mainWindow;
let tray;

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

function startBackend() {
  const projectRoot = app.isPackaged
    ? process.resourcesPath
    : path.resolve(__dirname, "../..");
  const developmentPython = path.join(projectRoot, ".venv", "bin", "python");
  const bundledBackend = path.join(process.resourcesPath, "jarvis-backend");
  const environment = {
    ...process.env,
    PYTHONPATH: projectRoot,
    JARVIS_API_PORT: "8003",
  };

  if (app.isPackaged) {
    environment.JARVIS_DATABASE_PATH = path.join(app.getPath("userData"), "jarvis.db");
  }

  const executable = app.isPackaged && fs.existsSync(bundledBackend)
    ? bundledBackend
    : process.env.JARVIS_PYTHON || developmentPython;
  const argumentsList = executable === bundledBackend
    ? []
    : ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8003"];
  backendProcess = spawn(executable, argumentsList, {
    cwd: projectRoot,
    env: environment,
    shell: false,
    stdio: "ignore",
  });
  backendProcess.on("error", (error) => {
    console.error("Could not start the JARVIS backend:", error.message);
  });
}

function stopBackend() {
  if (backendProcess && !backendProcess.killed) backendProcess.kill("SIGTERM");
  backendProcess = null;
}

async function restartBackend() {
  stopBackend();
  startBackend();
  const ready = await waitForBackend();
  if (!ready) {
    dialog.showErrorBox("JARVIS service", "The local JARVIS service did not become ready.");
  }
}

function createTray() {
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect x="1" y="1" width="30" height="30" rx="8" fill="#0c2939" stroke="#00c8ff"/><path d="M9 8h14v3h-5.5v13h-3V11H9z" fill="#00d5ff"/></svg>';
  const icon = nativeImage.createFromDataURL(
    `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`,
  );
  tray = new Tray(icon);
  tray.setToolTip("JARVIS AI Assistant");
  const setMenu = () => {
    tray.setContextMenu(Menu.buildFromTemplate([
      {
        label: "Show JARVIS",
        click: () => {
          if (!mainWindow) createWindow();
          else mainWindow.show();
        },
      },
      { label: "Hide window", click: () => mainWindow?.hide() },
      { label: "Restart local service", click: () => restartBackend() },
      { type: "separator" },
      {
        label: "Launch on login",
        type: "checkbox",
        checked: app.getLoginItemSettings().openAtLogin,
        click: (menuItem) => app.setLoginItemSettings({ openAtLogin: menuItem.checked }),
      },
      { type: "separator" },
      { label: "Quit JARVIS", click: () => app.quit() },
    ]));
  };
  setMenu();
  tray.on("click", () => {
    if (!mainWindow) createWindow();
    else if (mainWindow.isVisible()) mainWindow.hide();
    else mainWindow.show();
  });
}

function startStaticServer() {
  const webRoot = path.resolve(__dirname, "../dist");
  localServer = http.createServer((request, response) => {
    if (request.method !== "GET") {
      response.writeHead(405).end("Method not allowed");
      return;
    }

    let requestPath;
    try {
      requestPath = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
    } catch {
      response.writeHead(400).end("Invalid path");
      return;
    }

    const relativePath = requestPath === "/" ? "index.html" : requestPath.slice(1);
    const filePath = path.resolve(webRoot, relativePath);
    if (!filePath.startsWith(`${webRoot}${path.sep}`) && filePath !== path.join(webRoot, "index.html")) {
      response.writeHead(403).end("Forbidden");
      return;
    }

    fs.readFile(filePath, (error, contents) => {
      if (error) {
        response.writeHead(404).end("Not found");
        return;
      }
      response.writeHead(200, {
        "Content-Type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream",
        "X-Content-Type-Options": "nosniff",
      });
      response.end(contents);
    });
  });

  return new Promise((resolve, reject) => {
    localServer.once("error", reject);
    localServer.listen(0, "127.0.0.1", () => {
      const { port } = localServer.address();
      resolve(`http://127.0.0.1:${port}`);
    });
  });
}

function getStaticServerUrl() {
  const address = localServer?.address();
  return address && typeof address === "object"
    ? `http://127.0.0.1:${address.port}`
    : null;
}

function waitForBackend(timeoutMs = 15000) {
  const startedAt = Date.now();
  return new Promise((resolve) => {
    const probe = () => {
      const request = http.get("http://127.0.0.1:8003/health", (response) => {
        response.resume();
        if (response.statusCode === 200) {
          resolve(true);
        } else if (Date.now() - startedAt >= timeoutMs) {
          resolve(false);
        } else {
          setTimeout(probe, 300);
        }
      });
      request.setTimeout(800, () => request.destroy());
      request.on("error", () => {
        if (Date.now() - startedAt >= timeoutMs) resolve(false);
        else setTimeout(probe, 300);
      });
    };
    probe();
  });
}

async function createWindow() {
  const appUrl = getStaticServerUrl() || await startStaticServer();
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 920,
    minHeight: 640,
    backgroundColor: "#080e19",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith(appUrl)) {
      event.preventDefault();
      if (url.startsWith("https://")) shell.openExternal(url);
    }
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  await mainWindow.loadURL(appUrl);
}

app.whenReady().then(async () => {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission !== "media") {
      callback(false);
      return;
    }
    dialog.showMessageBox(mainWindow, {
      type: "question",
      buttons: ["Allow microphone", "Deny"],
      defaultId: 1,
      cancelId: 1,
      title: "Microphone permission",
      message: "Allow JARVIS to use the microphone for push-to-listen voice input?",
    }).then(({ response }) => callback(response === 0));
  });

  startBackend();
  await waitForBackend();
  await createWindow();
  createTray();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopBackend();
  localServer?.close();
});