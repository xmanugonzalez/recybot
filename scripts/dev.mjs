import { createHash, randomBytes } from 'node:crypto'
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { resolve } from 'node:path'
import process from 'node:process'

const ROOT = resolve(import.meta.dirname, '..')
const IS_WINDOWS = process.platform === 'win32'
const IS_RASPBERRY_PI = process.platform === 'linux' && (process.arch === 'arm' || process.arch === 'arm64')
const SERVER_CAMERA = process.argv.includes('--server-camera') || IS_RASPBERRY_PI
const VENV_PYTHON = resolve(
  ROOT,
  '.venv',
  IS_WINDOWS ? 'Scripts/python.exe' : 'bin/python',
)
const REQUIREMENTS = resolve(ROOT, 'ai/requirements-local.txt')
const CAMERA_REQUIREMENTS = resolve(ROOT, 'ai/requirements-camera.txt')
const REQUIREMENTS_MARKER = resolve(ROOT, '.venv/.recybot-requirements.sha256')
const TOKEN_PATH = resolve(ROOT, 'ai/config/api-token')
const OPENAI_KEY_PATH = resolve(ROOT, 'ai/config/openai-api-key')
const ROBOFLOW_KEY_PATH = resolve(ROOT, 'ai/config/roboflow-api-key')
const VITE_ENV_PATH = resolve(ROOT, '.env.recybot-dev.local')
const children = new Map()
let stopping = false
let exitCode = 0
let shutdownInputHandler

const RASPBERRY_SERVICES = [
  'recybot-pantalla.service',
  'recybot-web.service',
  'recybot-camera.service',
  'recybot-ia.service',
]
const DEVELOPMENT_PORTS = [5173, 8080, 8765, 8766]

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: options.capture ? 'pipe' : 'inherit',
    ...options,
  })
  if (result.error || result.status !== 0) {
    const detail = result.error?.message || result.stderr?.trim() || `${command} terminó con código ${result.status}`
    throw new Error(detail)
  }
  return result.stdout?.trim() ?? ''
}

async function prepareRaspberryDevelopment() {
  if (!IS_RASPBERRY_PI) return

  console.log('[config] Deteniendo servicios instalados de Recybot…')
  for (const service of RASPBERRY_SERVICES) {
    spawnSync('systemctl', ['--user', 'stop', service], {
      cwd: ROOT,
      encoding: 'utf8',
      stdio: 'ignore',
    })
  }

  console.log('[config] Liberando puertos de ejecuciones anteriores…')
  for (const port of DEVELOPMENT_PORTS) {
    spawnSync('fuser', ['-k', '-TERM', `${port}/tcp`], { stdio: 'ignore' })
  }
  await new Promise((resolveWait) => setTimeout(resolveWait, 1_000))
  for (const port of DEVELOPMENT_PORTS) {
    spawnSync('fuser', ['-k', '-KILL', `${port}/tcp`], { stdio: 'ignore' })
  }
}

function findPython() {
  const candidates = IS_WINDOWS
    ? [['py', ['-3.12']], ['python', []]]
    : [['python3.12', []], ['python3', []], ['python', []]]
  for (const [command, args] of candidates) {
    const result = spawnSync(command, [...args, '--version'], { encoding: 'utf8' })
    if (!result.error && result.status === 0) return { command, args }
  }
  throw new Error('No se encontró Python. Instala Python 3.12 y vuelve a ejecutar pnpm dev.')
}

async function ensurePython() {
  if (!existsSync(VENV_PYTHON)) {
    const python = findPython()
    console.log('[config] Creando el entorno Python .venv…')
    run(python.command, [...python.args, '-m', 'venv', '.venv'])
  }

  const requirementFiles = [REQUIREMENTS]
  if (SERVER_CAMERA && !IS_RASPBERRY_PI) requirementFiles.push(CAMERA_REQUIREMENTS)
  const requirements = Buffer.concat(await Promise.all(requirementFiles.map((file) => readFile(file))))
  const fingerprint = createHash('sha256').update(requirements).digest('hex')
  const installed = existsSync(REQUIREMENTS_MARKER)
    ? (await readFile(REQUIREMENTS_MARKER, 'utf8')).trim()
    : ''
  if (installed !== fingerprint) {
    console.log('[config] Instalando dependencias Python locales…')
    for (const requirementsFile of requirementFiles) {
      run(VENV_PYTHON, ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', requirementsFile])
    }
    await writeFile(REQUIREMENTS_MARKER, `${fingerprint}\n`)
  }
}

async function readSecret(prompt, missingPath) {
  if (!process.stdin.isTTY || !process.stdin.setRawMode) {
    throw new Error(`Falta ${missingPath}. Configura la clave antes de iniciar.`)
  }
  process.stdout.write(prompt)
  process.stdin.setRawMode(true)
  process.stdin.resume()
  let value = ''
  return new Promise((resolveSecret, reject) => {
    const onData = (chunk) => {
      for (const character of chunk.toString()) {
        if (character === '\u0003') {
          finish()
          reject(new Error('Configuración cancelada.'))
          return
        }
        if (character === '\r' || character === '\n') {
          finish()
          process.stdout.write('\n')
          resolveSecret(value.trim())
          return
        }
        if (character === '\u007f' || character === '\b') {
          if (value) {
            value = value.slice(0, -1)
            process.stdout.write('\b \b')
          }
          continue
        }
        value += character
        process.stdout.write('*')
      }
    }
    const finish = () => {
      process.stdin.off('data', onData)
      process.stdin.setRawMode(false)
      process.stdin.pause()
    }
    process.stdin.on('data', onData)
  })
}

async function ensureSecrets() {
  await mkdir(resolve(ROOT, 'ai/config'), { recursive: true })
  if (!existsSync(TOKEN_PATH)) {
    await writeFile(TOKEN_PATH, `${randomBytes(32).toString('hex')}\n`, { mode: 0o600 })
    console.log('[config] Token interno generado en ai/config/api-token.')
  }
  if (!existsSync(OPENAI_KEY_PATH) && !process.env.OPENAI_API_KEY) {
    const key = await readSecret('[config] API key de OpenAI: ', OPENAI_KEY_PATH)
    if (!key) throw new Error('La clave de OpenAI no puede estar vacía.')
    await writeFile(OPENAI_KEY_PATH, `${key}\n`, { mode: 0o600 })
    console.log('[config] Clave de OpenAI guardada localmente; Git la ignora.')
  }
  if (!existsSync(ROBOFLOW_KEY_PATH) && !process.env.ROBOFLOW_API_KEY) {
    const key = await readSecret('[config] Private API Key de Roboflow: ', ROBOFLOW_KEY_PATH)
    if (!key) throw new Error('La clave de Roboflow no puede estar vacía.')
    await writeFile(ROBOFLOW_KEY_PATH, `${key}\n`, { mode: 0o600 })
    console.log('[config] Clave guardada localmente; Git la ignora.')
  }
}

async function writeViteEnvironment() {
  const source = SERVER_CAMERA ? 'server' : 'device'
  await writeFile(
    VITE_ENV_PATH,
    `RECYBOT_BRIDGE_URL=http://127.0.0.1:8080\nVITE_CAMERA_SOURCE=${source}\n`,
  )
}

function prefixOutput(name, stream, target) {
  let pending = ''
  stream.setEncoding('utf8')
  stream.on('data', (chunk) => {
    pending += chunk
    const lines = pending.split(/\r?\n/)
    pending = lines.pop() ?? ''
    for (const line of lines) {
      if (line) target.write(`[${name}] ${line}\n`)
    }
  })
  stream.on('end', () => {
    if (pending) target.write(`[${name}] ${pending}\n`)
  })
}

function start(name, command, args, environment = {}) {
  const child = spawn(command, args, {
    cwd: ROOT,
    env: { ...process.env, ...environment },
    detached: !IS_WINDOWS,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  children.set(name, child)
  prefixOutput(name, child.stdout, process.stdout)
  prefixOutput(name, child.stderr, process.stderr)
  child.on('error', (error) => {
    console.error(`[${name}] No se pudo iniciar: ${error.message}`)
    exitCode = 1
    void stopAll()
  })
  child.on('exit', (code, signal) => {
    children.delete(name)
    if (stopping) return
    console.error(`[${name}] Se detuvo inesperadamente (${signal ?? `código ${code}`}).`)
    exitCode = code || 1
    void stopAll()
  })
}

async function waitFor(name, url, timeoutMs = 30_000) {
  const limit = Date.now() + timeoutMs
  while (Date.now() < limit && !stopping) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1_500) })
      if (response.ok) return
    } catch {
      // El servicio todavía está iniciando.
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 300))
  }
  throw new Error(`${name} no respondió en ${url}`)
}

function stopProcessTree(child) {
  if (!child.pid) return
  if (IS_WINDOWS) {
    spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
      stdio: 'ignore',
      windowsHide: true,
    })
    return
  }
  try {
    process.kill(-child.pid, 'SIGTERM')
  } catch {
    // El proceso ya terminó.
  }
}

function restoreInput() {
  if (!shutdownInputHandler) return
  process.stdin.off('data', shutdownInputHandler)
  if (process.stdin.isTTY && process.stdin.setRawMode) process.stdin.setRawMode(false)
  process.stdin.pause()
  shutdownInputHandler = undefined
}

function enableShutdownInput() {
  if (!process.stdin.isTTY || !process.stdin.setRawMode) return
  shutdownInputHandler = (chunk) => {
    const input = chunk.toString().toLowerCase()
    if (input.includes('\u0003') || input.includes('q')) void stopAll()
  }
  process.stdin.setRawMode(true)
  process.stdin.resume()
  process.stdin.on('data', shutdownInputHandler)
}

async function stopAll() {
  if (stopping) return
  stopping = true
  restoreInput()
  console.log('\n[recybot] Deteniendo todos los servicios…')
  const runningChildren = [...children.values()]
  for (const child of runningChildren) stopProcessTree(child)
  await new Promise((resolveWait) => setTimeout(resolveWait, 1_000))
  if (!IS_WINDOWS) {
    for (const child of runningChildren) {
      if (!child.pid) continue
      try {
        process.kill(-child.pid, 'SIGKILL')
      } catch {
        // El grupo ya terminó correctamente.
      }
    }
  }
  children.clear()
  console.log('[recybot] Todo quedó detenido.')
  process.exit(exitCode)
}

async function main() {
  await prepareRaspberryDevelopment()
  await ensurePython()
  await ensureSecrets()
  await writeViteEnvironment()

  const commonPython = {
    PYTHONUNBUFFERED: '1',
  }
  if (SERVER_CAMERA) {
    const cameraPython = IS_RASPBERRY_PI ? '/usr/bin/python3' : VENV_PYTHON
    const cameraScript = IS_RASPBERRY_PI ? 'camera/stream_server.py' : 'camera/camera_server.py'
    start('camara', cameraPython, [cameraScript], {
      ...commonPython,
      RECYBOT_CAMERA_BACKEND: process.env.RECYBOT_CAMERA_BACKEND || (IS_RASPBERRY_PI ? 'picamera2' : 'opencv'),
      RECYBOT_CAMERA_INDEX: process.env.RECYBOT_CAMERA_INDEX || '0',
      RECYBOT_CAMERA_FLIP_HORIZONTAL:
        process.env.RECYBOT_CAMERA_FLIP_HORIZONTAL || (IS_RASPBERRY_PI ? 'true' : 'false'),
    })
    await waitFor('Cámara', 'http://127.0.0.1:8765/api/camara/status')
  }

  start('ia', VENV_PYTHON, ['ai/server.py'], {
    ...commonPython,
    RECYBOT_INFERENCE_BACKEND: process.env.RECYBOT_INFERENCE_BACKEND || 'openai',
    RECYBOT_DEVICE_LABEL: process.env.RECYBOT_DEVICE_LABEL || 'PC local',
  })
  await waitFor('IA', 'http://127.0.0.1:8766/api/salud')

  start('puente', VENV_PYTHON, ['camera/web_bridge.py'], {
    ...commonPython,
    RECYBOT_CAMERA_URL: 'http://127.0.0.1:8765',
    RECYBOT_AI_URL: 'http://127.0.0.1:8766',
    RECYBOT_API_TOKEN_PATH: TOKEN_PATH,
  })

  start('web', process.execPath, ['node_modules/vite/bin/vite.js', '--host', '0.0.0.0', '--mode', 'recybot-dev'])
  await waitFor('Vite', 'http://127.0.0.1:5173')

  console.log('\n[recybot] Sistema listo en http://localhost:5173/')
  console.log('[recybot] Presioná Ctrl+C o Q para apagar absolutamente todo.\n')
  enableShutdownInput()
}

process.once('SIGINT', () => void stopAll())
process.once('SIGTERM', () => void stopAll())
process.once('uncaughtException', (error) => {
  console.error(`[recybot] ${error.stack || error.message}`)
  exitCode = 1
  void stopAll()
})
process.once('unhandledRejection', (error) => {
  console.error(`[recybot] ${error instanceof Error ? error.stack : error}`)
  exitCode = 1
  void stopAll()
})

main().catch((error) => {
  console.error(`[recybot] ${error.message}`)
  exitCode = 1
  void stopAll()
})
