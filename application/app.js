const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let pythonProcess = null;
let pendingRequests = new Map();
let requestId = 0;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        },
        show: false
    });

    mainWindow.loadFile('index.html');
    
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    
}

function getPythonExecutable() {
    if (app.isPackaged) {
        return path.join(process.resourcesPath, 'python', 'runtime', 'python.exe');
    } else {
        return process.platform === 'win32' ? 'python' : 'python3';
    }
}

function getScriptPath() {
    if (app.isPackaged) {
        return path.join(process.resourcesPath, 'python', 'tracker.py');
    } else {
        return path.join(__dirname, 'python', 'tracker.py');
    }
}

function startPythonProcess() {
    const pythonExe = getPythonExecutable();
    const scriptPath = getScriptPath();

    console.log(`[Python] Запуск: "${pythonExe}" "${scriptPath}"`);

    if (app.isPackaged) {
        if (!fs.existsSync(pythonExe)) {
            console.error(`[Python] python.exe не найден по пути: ${pythonExe}`);
            return;
        }
        if (!fs.existsSync(scriptPath)) {
            console.error(`[Python] tracker.py не найден по пути: ${scriptPath}`);
            return;
        }
    }

    const env = { ...process.env };
    if (app.isPackaged) {
        const sitePackagesPath = path.join(process.resourcesPath, 'python', 'runtime', 'Lib', 'site-packages');
        env.PYTHONPATH = sitePackagesPath;
        console.log(`[Python] PYTHONPATH: ${sitePackagesPath}`);
    }

    pythonProcess = spawn(pythonExe, [scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: env
    });

    pythonProcess.on('error', (err) => {
        console.error('[Python] Ошибка spawn:', err);
        pythonProcess = null;
    });

    pythonProcess.on('spawn', () => {
        console.log('[Python] Процесс успешно запущен');
    });

    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log('[Python stdout]:', output.trim());

        const lines = output.split('\n');
        for (const line of lines) {
            if (line.trim()) {
                try {
                    const response = JSON.parse(line);
                    const reqId = response._requestId;
                    if (reqId && pendingRequests.has(reqId)) {
                        const { resolve } = pendingRequests.get(reqId);
                        pendingRequests.delete(reqId);
                        resolve(response);
                    }
                } catch (e) {
                    // Не JSON
                }
            }
        }
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error('[Python stderr]:', data.toString().trim());
    });

    pythonProcess.on('close', (code) => {
        console.log(`[Python] Процесс завершился с кодом ${code}`);
        pythonProcess = null;
    });
}

ipcMain.handle('python-request', async (event, request) => {
    if (!pythonProcess || pythonProcess.killed) {
        console.log('[IPC] Перезапуск Python...');
        startPythonProcess();
        await new Promise(resolve => setTimeout(resolve, 1500));
    }

    if (!pythonProcess) {
        // Попробуем ещё раз и выведем подробности
        console.error('[IPC] Python-процесс всё ещё null после попытки запуска');
        throw new Error('Не удалось запустить Python-процесс');
    }

    return new Promise((resolve, reject) => {
        const id = ++requestId;
        request._requestId = id;
        pendingRequests.set(id, { resolve, reject });

        console.log(`[IPC] Отправка запроса ${id}: ${request.command}`);
        try {
            pythonProcess.stdin.write(JSON.stringify(request) + '\n');
        } catch (e) {
            console.error('[IPC] Ошибка записи в stdin:', e);
            reject(e);
            return;
        }

        setTimeout(() => {
            if (pendingRequests.has(id)) {
                pendingRequests.delete(id);
                reject(new Error(`Таймаут ответа от Python для команды ${request.command}`));
            }
        }, 30000);
    });
});

app.whenReady().then(() => {
    startPythonProcess();
    createWindow();
});

app.on('window-all-closed', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});