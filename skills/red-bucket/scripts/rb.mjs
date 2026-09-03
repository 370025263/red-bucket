#!/usr/bin/env node
// red-bucket 客户端。只用 Node 内建模块：没有 sh、curl、unzip、jq。
// 用法见 SKILL.md；node 18+（需要全局 fetch）。
import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from 'node:fs'
import { basename, dirname, join, resolve, sep } from 'node:path'
import { homedir } from 'node:os'
import { inflateRawSync } from 'node:zlib'
import process from 'node:process'

// 每次改这份文件都把版本号抬一下。服务器按 User-Agent 就能看出线上
// 还有多少老副本；npx skills 自己只认 git 哈希，不认这个数。
const CLIENT_VERSION = '0.3.0'
const USER_AGENT = `red-bucket-client/${CLIENT_VERSION} node/${process.versions.node}`
const DEFAULT_ORIGIN = 'https://redbucket.store'
const DEFAULT_PORTS = { 'http:': '80', 'https:': '443' }
// harness 列表故意不写死在这里。服务器随时会加新的（比如 cursor），
// 而装出去的每份副本都是冻结的：本地校验会让新 harness 被老客户端
// 拒绝，请求根本到不了服务器。合法值只从 /translation-matrix 取。

class Fail extends Error {}

// origin 是 authfile 的键，两边都必须先归一化，否则同一台服务器会存成多条。
function normOrigin(raw) {
  let parsed
  try {
    parsed = new URL(raw)
  } catch {
    throw new Fail(`not a URL: ${raw}`)
  }
  if (!DEFAULT_PORTS[parsed.protocol]) {
    throw new Fail(`origin must be http or https: ${raw}`)
  }
  const port = parsed.port && parsed.port !== DEFAULT_PORTS[parsed.protocol] ? `:${parsed.port}` : ''
  return `${parsed.protocol}//${parsed.hostname.toLowerCase()}${port}`
}

function authPath() {
  if (process.env.RED_BUCKET_AUTH) return process.env.RED_BUCKET_AUTH
  if (process.platform === 'win32' && process.env.APPDATA) {
    return join(process.env.APPDATA, 'red-bucket', 'auth.json')
  }
  const base = process.env.XDG_CONFIG_HOME || join(homedir(), '.config')
  return join(base, 'red-bucket', 'auth.json')
}

// 读不懂的文件当作没有凭据，并且绝不覆盖它：里面可能是别的工具的 token。
function readAuth() {
  const path = authPath()
  if (!existsSync(path)) return { doc: { version: 1, hosts: {} }, writable: true }
  let doc
  try {
    doc = JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    return { doc: { version: 1, hosts: {} }, writable: false, reason: 'unreadable' }
  }
  if (!doc || typeof doc !== 'object' || doc.version !== 1) {
    return { doc: { version: 1, hosts: {} }, writable: false, reason: 'unknown-version' }
  }
  if (!doc.hosts || typeof doc.hosts !== 'object') doc.hosts = {}
  return { doc, writable: true }
}

function writeAuth(doc) {
  const path = authPath()
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 })
  const tmp = `${path}.${process.pid}.tmp`
  writeFileSync(tmp, `${JSON.stringify(doc, null, 2)}\n`, { mode: 0o600 })
  renameSync(tmp, path)
}

function tokenFor(origin) {
  if (process.env.RED_BUCKET_TOKEN) return { token: process.env.RED_BUCKET_TOKEN, source: 'env' }
  const { doc, reason } = readAuth()
  if (reason) return { token: null, source: reason }
  const entry = doc.hosts[origin]
  if (!entry || !entry.token) return { token: null, source: 'anonymous' }
  return { token: entry.token, source: 'authfile', username: entry.username }
}

async function call(origin, method, path, { body, token, accept } = {}) {
  const headers = { 'user-agent': USER_AGENT }
  if (body !== undefined) headers['content-type'] = 'application/json'
  if (token) headers.authorization = `Bearer ${token}`
  if (accept) headers.accept = accept
  const resp = await fetch(origin + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return resp
}

async function json(resp) {
  const text = await resp.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    throw new Fail(`server sent non-JSON (HTTP ${resp.status})`)
  }
}

const sleep = (ms) => new Promise((done) => setTimeout(done, ms))

// 一次 login 不一定等得到人点授权：agent 的 shell 常常 30 秒就超时。
// 所以把进行中的 device_code 落在 pending.json，login 只等 --wait 秒；
// 人点完之后再跑一次 login 或 status，接着上次的码把 token 领回来。
function pendingPath() {
  return join(dirname(authPath()), 'pending.json')
}

function readPending(origin) {
  const path = pendingPath()
  if (!existsSync(path)) return null
  try {
    const doc = JSON.parse(readFileSync(path, 'utf8'))
    const item = doc && doc.hosts ? doc.hosts[origin] : null
    if (!item || !item.device_code) return null
    if (new Date(item.expires_at).getTime() <= Date.now()) return null
    return item
  } catch {
    return null
  }
}

function writePending(origin, item) {
  const path = pendingPath()
  let doc = { version: 1, hosts: {} }
  try {
    if (existsSync(path)) doc = JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    doc = { version: 1, hosts: {} }
  }
  if (!doc.hosts) doc.hosts = {}
  if (item) doc.hosts[origin] = item
  else delete doc.hosts[origin]
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 })
  const tmp = `${path}.${process.pid}.tmp`
  writeFileSync(tmp, JSON.stringify(doc, null, 2) + '\n', { mode: 0o600 })
  renameSync(tmp, path)
}

function saveToken(origin, state, client) {
  const { doc, writable, reason } = readAuth()
  if (!writable) throw new Fail(`${authPath()} is ${reason}; fix or move it, then run login again.`)
  doc.hosts[origin] = {
    username: state.user.username,
    token: state.token,
    created_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    client,
  }
  writeAuth(doc)
}

// 轮询一个进行中的码，最多 waitMs。返回 'approved' | 'waiting'；拒绝和过期直接抛。
async function collect(origin, item, waitMs) {
  const deadline = Math.min(Date.now() + waitMs, new Date(item.expires_at).getTime())
  for (;;) {
    const polled = await call(origin, 'POST', '/api/v1/auth/device/token', {
      body: { device_code: item.device_code },
    })
    if (polled.status === 404) {
      writePending(origin, null)
      throw new Fail('that sign-in code expired or was already used. Run login again.')
    }
    const state = await json(polled)
    if (state.status === 'denied') {
      writePending(origin, null)
      throw new Fail('sign-in was refused in the browser.')
    }
    if (state.status === 'approved') {
      saveToken(origin, state, item.client)
      writePending(origin, null)
      return `Signed in as ${state.user.username}.`
    }
    if (Date.now() >= deadline) return null
    await sleep(Math.min(item.interval * 1000, Math.max(0, deadline - Date.now())))
  }
}

function stillWaiting(item) {
  return (
    `Not approved yet. The link is still valid until ${item.expires_at}:\n` +
    `  ${item.url}\n` +
    `Code ${item.user_code}. After approving in the browser, run login (or status) again to finish.`
  )
}

async function login(origin, client, waitSeconds) {
  const existing = tokenFor(origin)
  if (existing.token && existing.source === 'authfile') {
    const check = await call(origin, 'GET', '/api/v1/users/me', { token: existing.token })
    if (check.ok) {
      const who = await json(check)
      return `Already signed in as ${who.username}.`
    }
  }
  let item = readPending(origin)
  if (!item) {
    const started = await call(origin, 'POST', '/api/v1/auth/device', { body: { client } })
    if (started.status !== 201) throw new Fail(`could not start sign-in (HTTP ${started.status})`)
    const grant = await json(started)
    item = {
      device_code: grant.device_code,
      user_code: grant.user_code,
      url: grant.verification_url_complete,
      interval: grant.interval,
      expires_at: new Date(Date.now() + grant.expires_in * 1000).toISOString().replace(/\.\d+Z$/, 'Z'),
      client,
    }
    writePending(origin, item)
  }
  process.stdout.write(
    `Open this in a browser to sign in or create an account:\n` +
      `  ${item.url}\n` +
      `The page should show the code ${item.user_code}. Waiting up to ${waitSeconds}s...\n`,
  )
  const done = await collect(origin, item, waitSeconds * 1000)
  return done || stillWaiting(item)
}

async function logout(origin) {
  const held = tokenFor(origin)
  if (!held.token) return 'Not signed in.'
  // 服务端撤销和本地删除必须都做，只做一半会留下活 token 或死条目。
  const revoked = await call(origin, 'POST', '/api/v1/auth/logout', { body: {}, token: held.token })
  const { doc, writable } = readAuth()
  if (writable && doc.hosts[origin]) {
    delete doc.hosts[origin]
    writeAuth(doc)
  }
  return revoked.ok ? 'Signed out.' : `Local credential removed; server said HTTP ${revoked.status}.`
}

async function status(origin) {
  const held0 = tokenFor(origin)
  if (!held0.token) {
    const item = readPending(origin)
    if (item) {
      const done = await collect(origin, item, 0)
      if (done) return done
      return stillWaiting(item)
    }
  }
  const held = tokenFor(origin)
  if (held.source === 'unreadable') return `${authPath()} will not parse. Treating you as signed out.`
  if (held.source === 'unknown-version') return `${authPath()} is a format I do not know. Treating you as signed out.`
  if (!held.token) return `Not signed in to ${origin}.`
  const resp = await call(origin, 'GET', '/api/v1/users/me', { token: held.token })
  if (resp.status === 401) return `Credential for ${origin} is no longer valid. Run login.`
  if (!resp.ok) throw new Fail(`server said HTTP ${resp.status}`)
  const who = await json(resp)
  return `Signed in to ${origin} as ${who.username} (via ${held.source}).`
}

// —— zip：Python 的 zipfile 用 deflate 写，这里只需 stored 与 deflate 两种 ——

function findEocd(buf) {
  const floor = Math.max(0, buf.length - 65557)
  for (let at = buf.length - 22; at >= floor; at -= 1) {
    if (buf.readUInt32LE(at) === 0x06054b50) return at
  }
  throw new Fail('not a zip archive')
}

function safeJoin(dest, name) {
  const cleaned = name.replace(/\\/g, '/')
  if (cleaned.startsWith('/') || /^[a-zA-Z]:/.test(cleaned)) {
    throw new Fail(`archive holds an absolute path: ${name}`)
  }
  const full = resolve(dest, cleaned)
  if (full !== dest && !full.startsWith(dest + sep)) {
    throw new Fail(`archive tries to escape the destination: ${name}`)
  }
  return full
}

function unpack(buf, dest) {
  const eocd = findEocd(buf)
  const count = buf.readUInt16LE(eocd + 10)
  let at = buf.readUInt32LE(eocd + 16)
  const written = []
  for (let seen = 0; seen < count; seen += 1) {
    if (buf.readUInt32LE(at) !== 0x02014b50) throw new Fail('corrupt zip directory')
    const method = buf.readUInt16LE(at + 10)
    const compressed = buf.readUInt32LE(at + 20)
    const nameLen = buf.readUInt16LE(at + 28)
    const extraLen = buf.readUInt16LE(at + 30)
    const commentLen = buf.readUInt16LE(at + 32)
    const localAt = buf.readUInt32LE(at + 42)
    const name = buf.subarray(at + 46, at + 46 + nameLen).toString('utf8')
    at += 46 + nameLen + extraLen + commentLen
    if (name.endsWith('/')) continue
    if (buf.readUInt32LE(localAt) !== 0x04034b50) throw new Fail('corrupt zip entry')
    const dataAt = localAt + 30 + buf.readUInt16LE(localAt + 26) + buf.readUInt16LE(localAt + 28)
    const raw = buf.subarray(dataAt, dataAt + compressed)
    let body
    if (method === 0) body = raw
    else if (method === 8) body = inflateRawSync(raw)
    else throw new Fail(`unsupported zip compression ${method} for ${name}`)
    const full = safeJoin(dest, name)
    mkdirSync(dirname(full), { recursive: true })
    writeFileSync(full, body)
    written.push(name)
  }
  return written
}

// 只在出错时才问服务器，正常路径不多一次往返。
// 必须翻页：矩阵条目数随 harness 数平方增长，早晚超过 per_page 上限。
async function knownTargets(origin) {
  const seen = new Set()
  for (let page = 1; page <= 20; page += 1) {
    const resp = await call(origin, 'GET', `/api/v1/translation-matrix?page=${page}&per_page=100`)
    if (!resp.ok) break
    const body = await json(resp)
    for (const row of body.items || []) seen.add(row.target)
    if (!body.has_more) break
  }
  return [...seen].sort()
}

async function targetHelp(origin, tried) {
  let known = []
  try {
    known = await knownTargets(origin)
  } catch {
    // 网络问题就退回泛化提示，不要拿一份过期的本地清单去骗人。
  }
  const lead = tried
    ? `--target ${tried} is not something ${origin} translates to`
    : '--target is required'
  return known.length ? `${lead}. It knows: ${known.join(', ')}` : `${lead}.`
}

async function install(origin, slug, target, dest) {
  const match = /^([^/]+)\/([^/]+)$/.exec(slug || '')
  if (!match) throw new Fail('name the bucket as <user>/<bucket>')
  if (!target) throw new Fail(await targetHelp(origin, target))
  const held = tokenFor(origin)
  const path =
    `/api/v1/users/${encodeURIComponent(match[1])}` +
    `/buckets/${encodeURIComponent(match[2])}/translated?target=${target}`
  const resp = await call(origin, 'GET', path, { token: held.token, accept: 'application/zip' })
  if (resp.status === 422) throw new Fail(await targetHelp(origin, target))
  if (resp.status === 404) {
    throw new Fail(
      held.token
        ? `${slug} does not exist, or is private and not yours.`
        : `${slug} does not exist, or is private. If it is yours, run login first.`,
    )
  }
  if (!resp.ok) throw new Fail(`server said HTTP ${resp.status}`)
  const buf = Buffer.from(await resp.arrayBuffer())
  const root = resolve(dest)
  mkdirSync(root, { recursive: true })
  if (!statSync(root).isDirectory()) throw new Fail(`${root} is not a directory`)
  const written = unpack(buf, root)
  return `Installed ${written.length} file(s) from ${slug} as ${target} into ${root}.`
}

// 发布侧。文件内容从本地目录读，agent 不用手拼 JSON，也不会把
// 二进制当文本发坏。
function splitSlug(slug) {
  const match = /^([^/]+)\/([^/]+)$/.exec(slug || '')
  if (!match) throw new Fail('name the bucket as <user>/<bucket>')
  return { user: match[1], bucket: match[2] }
}

function requireToken(origin) {
  const held = tokenFor(origin)
  if (!held.token) throw new Fail(`not signed in to ${origin}. Run login first.`)
  return held.token
}

// 把服务器的错误信封翻成一句人能看懂的话；details 里的 path/field 都带上。
async function explain(resp, fallback) {
  let err = null
  try {
    err = (await json(resp)).error
  } catch {
    // 不是 JSON 就只报状态码
  }
  if (!err) return `${fallback} (HTTP ${resp.status})`
  const bits = (err.details || []).map((item) => {
    const where = item.path || item.field || ''
    const what = item.message || item.issue || ''
    return where ? `${where}: ${what}` : what
  })
  return bits.length ? `${err.message}: ${bits.join('; ')}` : `${err.message} (HTTP ${resp.status})`
}

async function create(origin, slug, flags) {
  const { user, bucket } = splitSlug(slug)
  const token = requireToken(origin)
  const body = {
    name: bucket,
    visibility: flags.visibility || 'private',
    description: flags.description || '',
  }
  if (flags.template) body.template = flags.template
  const resp = await call(origin, 'POST', `/api/v1/users/${encodeURIComponent(user)}/buckets`, { body, token })
  if (resp.status !== 201) throw new Fail(await explain(resp, 'could not create bucket'))
  const made = await json(resp)
  return `Created ${user}/${bucket} (${made.visibility}). Page: ${origin}/${user}/${bucket}`
}

function walk(root, dir = root, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '.git' || entry.name === 'node_modules') continue
    const full = join(dir, entry.name)
    if (entry.isDirectory()) walk(root, full, out)
    else if (entry.isFile()) out.push(full)
  }
  return out
}

// 能无损往返 UTF-8 的当文本发，否则 base64；服务器两种都收。
function fileEntry(root, full) {
  const raw = readFileSync(full)
  const rel = full.slice(root.length + 1).split(sep).join('/')
  const text = raw.toString('utf8')
  if (Buffer.from(text, 'utf8').equals(raw)) return { path: rel, content_text: text }
  return { path: rel, content_base64: raw.toString('base64') }
}

async function upload(origin, slug, dir, flags) {
  const { user, bucket } = splitSlug(slug)
  const token = requireToken(origin)
  if (!flags.type || !flags.harness) {
    throw new Fail('--type (skill|mcp|instructions|subagent|plugin) and --harness (which harness it was written for) are required')
  }
  const root = resolve(dir || '.')
  if (!existsSync(root) || !statSync(root).isDirectory()) throw new Fail(`${root} is not a directory`)
  const files = walk(root).map((full) => fileEntry(root, full))
  if (!files.length) throw new Fail(`${root} has no files`)
  const body = {
    type: flags.type,
    source_harness: flags.harness,
    path: flags.path || basename(root),
    files,
  }
  const resp = await call(
    origin,
    'POST',
    `/api/v1/users/${encodeURIComponent(user)}/buckets/${encodeURIComponent(bucket)}/assets`,
    { body, token },
  )
  if (resp.status !== 201) throw new Fail(await explain(resp, 'upload rejected'))
  const made = await json(resp)
  return `Uploaded ${files.length} file(s) as ${made.type} (${made.source_harness}) to ${user}/${bucket}/${made.path}.`
}

function readFlags(argv) {
  const flags = {}
  const loose = []
  for (let at = 0; at < argv.length; at += 1) {
    if (argv[at].startsWith('--')) {
      const next = argv[at + 1]
      // 没有值或紧跟着下一个 flag，就当开关；否则 --help 会吞掉后面的词。
      if (next === undefined || next.startsWith('--')) {
        flags[argv[at].slice(2)] = ''
      } else {
        flags[argv[at].slice(2)] = next
        at += 1
      }
    } else {
      loose.push(argv[at])
    }
  }
  return { flags, loose }
}

const USAGE = `red-bucket client (Node only)

  node rb.mjs login   [--origin URL] [--client NAME] [--wait SECONDS]
  node rb.mjs logout  [--origin URL]
  node rb.mjs status  [--origin URL]
  node rb.mjs version
  node rb.mjs install <user>/<bucket> --target <harness> [--dest DIR] [--origin URL]
  node rb.mjs create  <user>/<bucket> [--visibility private|public] [--description TEXT] [--template NAME]
  node rb.mjs upload  <user>/<bucket> <local-dir> --type <asset type> --harness <written-for> [--path bucket/path]

Run install without --target to have the server list the harnesses it
translates to; this client keeps no list of its own, so a harness added
to the server works here without updating the skill.

login prints a link, then waits --wait seconds (default 20) for the
browser approval. If that runs out it exits 0 and keeps the code; run
login or status again after approving and the token is collected. No
new code is issued while one is still valid.

upload sends every file under <local-dir> (text as text, anything else
as base64) as one asset rooted at --path, default the directory's name.
The server validates the asset (SKILL.md frontmatter, mcp shape, ...)
and prints exactly what is wrong if it refuses. create and upload need
a sign-in; run login first.

Origin defaults to $RED_BUCKET_URL, then ${DEFAULT_ORIGIN}.
The credential lives in ${'$RED_BUCKET_AUTH'} or the per-user config dir; it is never printed.
`

async function main(argv) {
  const { flags, loose } = readFlags(argv)
  const command = loose[0]
  if (!command || command === 'help' || flags.help !== undefined) {
    process.stdout.write(USAGE)
    return 0
  }
  if (command === 'version') {
    process.stdout.write(`${USER_AGENT}\n`)
    return 0
  }
  const origin = normOrigin(flags.origin || process.env.RED_BUCKET_URL || DEFAULT_ORIGIN)
  let said
  if (command === 'login') said = await login(origin, flags.client || 'unknown-agent', Number(flags.wait || 20) || 20)
  else if (command === 'logout') said = await logout(origin)
  else if (command === 'status') said = await status(origin)
  else if (command === 'install') said = await install(origin, loose[1], flags.target, flags.dest || process.env.RED_BUCKET_DEST || '.')
  else if (command === 'create') said = await create(origin, loose[1], flags)
  else if (command === 'upload') said = await upload(origin, loose[1], loose[2], flags)
  else throw new Fail(`unknown command: ${command}`)
  process.stdout.write(`${said}\n`)
  return 0
}

main(process.argv.slice(2))
  .then((code) => process.exit(code))
  .catch((err) => {
    process.stderr.write(`${err instanceof Fail ? err.message : err.stack}\n`)
    process.exit(1)
  })
