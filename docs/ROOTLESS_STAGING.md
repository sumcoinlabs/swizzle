# Rootless single-user temporary staging

Target: `electrumbtc1@159.118.235.181` (Ubuntu 20.04 x86_64). **No sudo, Docker, PM2, Nginx, systemd, firewall, or OS package operations.** Never run any of these scripts as root. The SSH key authenticates SSH, not sudo. Existing Bitcoin services remain untouched.

All runtime files, secrets, databases, software and logs live under `/home/electrumbtc1/.swizzle-stage/` with mode 0700 and the processes run with UID 1000. Python 3.13, PostgreSQL 16 and Valkey 9 are installed under this prefix using rootless micromamba/conda-forge. PostgreSQL (`127.0.0.1:15488`) and Valkey (`127.0.0.1:16388`) are private and authenticated, and the Gunicorn preview binds only `127.0.0.1:8788`.

## Setup

Download the release bundle from the chat, then from your Mac:

```sh
unzip -oq ~/Downloads/swizzle-rootless-v03.zip -d ~/Downloads && bash ~/Downloads/swizzle-rootless-v03/staging/apply-and-stage-from-mac.sh
```

The script refuses if the source branch is dirty, if the GitHub HEAD differs, if the rootless host or disk preconditions fail, if staging already exists, or if a target port is bound. It first publishes the stage scripts to GitHub, then uses SSH `BatchMode=yes` to verify the remote, and launches user-only installation. If an install fails midway, rerun the **uninstall** command below before retrying.

## Preview

In a second Mac terminal:

```sh
ssh -N -L 8988:127.0.0.1:8788 electrumbtc1@159.118.235.181
```

Browse `http://localhost:8988/` and `http://localhost:8988/admin/`. Staging credentials are generated on the server, mode 0600. Retrieve securely using:

```sh
ssh electrumbtc1@159.118.235.181 'cat ~/.swizzle-stage/private/admin-login.txt'
```

## Remove

Run from the Mac even if the remote install was partial:

```sh
bash ~/Downloads/swizzle-rootless-v03/staging/remove-from-mac.sh
```

The uninstall checks the username, exact fixed path, ownership, marker, daemon PIDs and `/proc` identity. It refuses to delete on unexpected processes. Only stops its PostgreSQL, Valkey, Gunicorn and (if added later) Celery processes, then deletes its own directory. It never touches any existing host application, global configuration, or files outside its staging prefix. **This removal intentionally deletes staging database and content.** There is no automatic backup or external server data mutation.

## Important limitations

This is a private SSH-tunneled **development** preview, not public production. Django DEBUG is true specifically to permit loopback HTTP. No domain, public port, payment credentials, AI API keys, advertisements, automated public publishing, or customer data may be used. For persistent public production use, provision a maintained OS and HTTPS, commit reviewed Django migrations, enable proper secure cookies, and introduce an explicit automated publishing policy. Background Celery/Valkey integration can be activated separately once feed configurations are vetted.

Installation depends on the remote being able to download GitHub, conda-forge and PyPI over TLS. It has not been executed against the live server by the assistant.
