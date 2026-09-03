"""生成 install-script 的正文。

产物是一段自包含的 Node 程序：只用 node 内建模块，不要 sh、curl、
unzip。它必须独立于 skills/red-bucket/scripts/rb.mjs——那份要先装
skill 才有，而这段是给「本机什么都没装」的人贴的。
"""
from __future__ import annotations

HEADER = "#!/usr/bin/env node\n"


def node_script(origin: str, rel: str) -> str:
    """拉取 translated 归档并按目标 harness 布局落盘。"""
    return HEADER + f"""// red-bucket install. Node 18+ only.
// No sh, curl, unzip, jq or npm packages.
import {{ mkdirSync, writeFileSync }} from 'node:fs'
import {{ dirname, resolve, sep }} from 'node:path'
import {{ inflateRawSync }} from 'node:zlib'
import process from 'node:process'

const BASE = process.env.RED_BUCKET_URL || '{origin}'
const DEST = resolve(process.env.RED_BUCKET_DEST || '.')
const PATH = '{rel}'

function findEocd(buf) {{
  const floor = Math.max(0, buf.length - 65557)
  for (let at = buf.length - 22; at >= floor; at -= 1) {{
    if (buf.readUInt32LE(at) === 0x06054b50) return at
  }}
  throw new Error('not a zip archive')
}}

function safeJoin(name) {{
  const clean = name.replace(/\\\\/g, '/')
  if (clean.startsWith('/') || /^[a-zA-Z]:/.test(clean)) {{
    throw new Error('absolute path in archive: ' + name)
  }}
  const full = resolve(DEST, clean)
  if (full !== DEST && !full.startsWith(DEST + sep)) {{
    throw new Error('path escapes destination: ' + name)
  }}
  return full
}}

function unpack(buf) {{
  const eocd = findEocd(buf)
  const count = buf.readUInt16LE(eocd + 10)
  let at = buf.readUInt32LE(eocd + 16)
  let made = 0
  for (let seen = 0; seen < count; seen += 1) {{
    if (buf.readUInt32LE(at) !== 0x02014b50) {{
      throw new Error('corrupt zip directory')
    }}
    const method = buf.readUInt16LE(at + 10)
    const size = buf.readUInt32LE(at + 20)
    const nameLen = buf.readUInt16LE(at + 28)
    const extraLen = buf.readUInt16LE(at + 30)
    const noteLen = buf.readUInt16LE(at + 32)
    const localAt = buf.readUInt32LE(at + 42)
    const name = buf
      .subarray(at + 46, at + 46 + nameLen)
      .toString('utf8')
    at += 46 + nameLen + extraLen + noteLen
    if (name.endsWith('/')) continue
    if (buf.readUInt32LE(localAt) !== 0x04034b50) {{
      throw new Error('corrupt zip entry')
    }}
    const dataAt =
      localAt + 30 +
      buf.readUInt16LE(localAt + 26) +
      buf.readUInt16LE(localAt + 28)
    const raw = buf.subarray(dataAt, dataAt + size)
    let body
    if (method === 0) body = raw
    else if (method === 8) body = inflateRawSync(raw)
    else throw new Error('unsupported compression ' + method)
    const full = safeJoin(name)
    mkdirSync(dirname(full), {{ recursive: true }})
    writeFileSync(full, body)
    made += 1
  }}
  return made
}}

const resp = await fetch(BASE + PATH, {{
  headers: {{ accept: 'application/zip' }},
}})
if (!resp.ok) {{
  process.stderr.write('red-bucket: HTTP ' + resp.status + '\\n')
  process.exit(1)
}}
mkdirSync(DEST, {{ recursive: true }})
const made = unpack(Buffer.from(await resp.arrayBuffer()))
process.stdout.write('red-bucket: wrote ' + made + ' file(s) to ' +
  DEST + '\\n')
"""
