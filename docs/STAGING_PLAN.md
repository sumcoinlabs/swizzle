# Safe temporary VM staging — first audit, then install

**No server has been modified and no port has been assigned.** Run the supplied `server-readonly-audit.sh` on the proposed SSH host before preparing any installation commands.

Target: `electrumbtc1@159.118.235.181` (proposed by repository owner). This host may run other software and must not be treated as disposable. The audit prints host capacity, current listening sockets, installed binaries, running service names, and privilege availability. It does not create directories, install packages, change firewall rules, or restart processes.

After review, stage in an isolated directory owned by a dedicated unprivileged user and bind the web app to a verified unused **127.0.0.1-only** TCP port. Access from the Mac through `ssh -L 8000:127.0.0.1:REMOTE_PORT electrumbtc1@159.118.235.181`, then browse to `http://localhost:8000`. **Never publicly expose a login, session, payment flow or Django DEBUG service over plain HTTP.** Payment keys and automated publication must remain disabled during this trial.

Prefer a uniquely named PostgreSQL database/user and Redis instance/namespace, only if the host can support them. Do not modify shared production services or config. Deploy with a dedicated service name and explicitly record created resources for clean removal. Before installation, produce an uninstall script that stops only the new service(s) and removes only the resources created by this staging install; never delete pre-existing processes or data.

Only attempt staging after CI reaches green and migration files are reviewed and committed. No live domain, DNS, MX records, SSL certificates or API keys are required for an SSH-tunneled preview.
