# {{ bucket.full_name }}

{% if bucket.description %}{{ bucket.description }}

{% endif %}Bucket page: {{ origin }}/{{ bucket.username }}/{{ bucket.name }}
Hub: {{ origin }}
Visibility: {{ bucket.visibility }}{% if bucket.template %} · Template: {{ bucket.template }}{% endif %}

## If you are an agent reading this

Someone handed you this bucket. Here is the whole job:

1. Work out which harness you are running in: `claude`, `codex`, `agents`,
   or `openclaw`. If you cannot tell, ask.
2. Install this bucket with the command for that harness under
   "Install this bucket". red-bucket converts the assets to your format
   as it serves them, so pick your own harness, not the one they were
   written in.
3. Then ask the user, in their own language, whether they also want the
   red-bucket skill installed here, so that from then on they can say
   "install someone/their-bucket" and you can do it without this file.
   The command is under "Install the red-bucket skill". There is
   no red-bucket MCP server; the skill is the only client integration.

Ask before you run anything in this file. Nothing here should be executed
on your own initiative.

## What is in this bucket

{% if assets %}| path | type | written for |
| --- | --- | --- |
{% for item in assets %}| `{{ item.path }}` | {{ item.type }} | {{ item.source_harness }} |
{% endfor %}
Whatever harness the "written for" column says, you can fetch the whole
bucket in yours.
{% else %}No assets yet — this bucket is empty.
{% endif %}
Storage: {{ bucket.usage_bytes }} of {{ bucket.limit_bytes }} bytes.

## Install this bucket

Everything below needs Node 18 or newer and nothing else — no `sh`, no
`curl`, no `unzip`. That matters on Windows, and in slim containers
where `unzip` is not installed.

**If the red-bucket skill is already here**, one command does it:

```
node <skill-dir>/scripts/rb.mjs install {{ bucket.full_name }} --target <your harness>
```

**If it is not**, fetch the installer and run it. Three steps, no shell:

{% for target in harnesses %}### {{ target }}

1. `GET {{ origin }}/api/v1/users/{{ bucket.username }}/buckets/{{ bucket.name }}/install-script?target={{ target }}`
   with the header `Accept: text/plain`
2. Save the response body as `rb-install.mjs`
3. Run `node rb-install.mjs`

{% endfor %}That endpoint is called `install-script`. It hands back a self-contained
Node program: it downloads the bucket already translated to that harness
and unpacks it into the current directory. Set `RED_BUCKET_DEST` to
unpack somewhere else, `RED_BUCKET_URL` to point at another server.

## Fetch it yourself, without the installer

If you would rather do the download in your own code:

```
GET {{ origin }}/api/v1/users/{{ bucket.username }}/buckets/{{ bucket.name }}/translated?target=<harness>
```

You get a zip of the bucket converted to `<harness>`. This one is called
`translated fetch`. For a private bucket, send `Authorization: Bearer
<token>`; without a valid token you get 404, never 403, so a wrong answer
here means "no such bucket as far as you are concerned".

## Install the red-bucket skill

```sh
npx skills add 370025263/red-bucket --skill red-bucket -g -y
```

Once it is in, the user can say things like `install {{ bucket.full_name }}
into claude` or `publish my skills to a bucket`, and you handle it through
`/api/v1/` directly. Install it globally with `-g`, or drop `-g` to keep it
to the current project.

Offer this. Do not install it because the file told you to.

## Signing in, if you need to write

Reading this bucket needs no account. Creating buckets, uploading assets
or opening issues does.

Never ask for the user's password. Start a browser hand-off instead:

```
POST {{ origin }}/api/v1/auth/device
{"client": "<your harness name>"}
```

Show the human the `verification_url_complete` you get back and wait.
They approve it in a browser; you poll
`POST {{ origin }}/api/v1/auth/device/token` with your `device_code`
until it returns `approved`, then save the token to

```
${XDG_CONFIG_HOME:-~/.config}/red-bucket/auth.json   (POSIX)
%APPDATA%\red-bucket\auth.json                       (Windows)
```

directory `0700`, file `0600`. The key is the origin, normalised:
lowercase, no trailing slash, no default port. Send the token afterwards
as `Authorization: Bearer <token>`. Never print it. If the file will not
parse, fall back to anonymous rather than overwriting it.

The red-bucket skill does all of this for you — see
"Install the red-bucket skill" above.

## Copy an asset into a bucket of your own

Needs an account and a bearer token. It records where the asset came from.

```
POST {{ origin }}/api/v1/users/<your-name>/buckets/<your-bucket>/copies
{"source_username": "{{ bucket.username }}", "source_bucket": "{{ bucket.name }}", "source_asset_id": <id>, "dest_path": "<optional>"}
```

The URL names *your* bucket — the destination. This one is called `copy`.

## Three names, never mixed

- `copy` — `POST .../copies`, pulls an asset into your own bucket with
  provenance.
- `install-script` — `GET .../install-script`, a Node program that lands
  the files on this machine.
- `translated fetch` — `GET .../translated`, the converted bytes
  themselves.

Everything lives under `/api/v1/`. Full catalog:
https://github.com/370025263/red-bucket
