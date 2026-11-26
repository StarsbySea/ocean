# ubuntu-slim offline execution: experiment record

## Decision

Use GitHub Actions custom default run shell, backed by util-linux unshare and setpriv already installed on the tested ubuntu-slim image. No wrapper or dependency installation is required.

```yaml
defaults:
  run:
    shell: >-
      unshare --user --map-current-user --net --keep-caps --
      setpriv --no-new-privs --bounding-set=-all
      --inh-caps=-all --ambient-caps=-all --
      bash --noprofile --norc -e -o pipefail {0}
```

Specify `shell: bash` only for explicit online setup and delivery run steps. Keep dependencies locked; use package-manager offline options where appropriate. Keep write credentials out of builds. This is a Linux-only shell; mixed-platform workflows should scope it to Linux jobs.

## Evidence

- [Round 1](https://github.com/StarsbySea/ocean/actions/runs/45885493237): mise, native Seccomp, unprivileged user+net namespaces and bubblewrap blocked direct network probes; Harden-Runner, nono, Landlock, bare unshare, sudo unshare, Docker, iptables and nftables were unavailable or ineffective. pytest-socket and pip offline were application/tool scoped.
- [Round 2](https://github.com/StarsbySea/ocean/actions/runs/45885642571): preserved UID/GID and asyncio with unshare current user; full capability bounding-set removal failed without keep-caps.
- [Round 3](https://github.com/StarsbySea/ocean/actions/runs/45885912982): keep-caps then setpriv dropped capability sets and set NoNewPrivs. Median launch time 8.97 ms (30 repetitions); bubblewrap minimal 3.82 ms; mise 15.89 ms; baseline 1.23 ms.
- [Native job default acceptance](https://github.com/StarsbySea/ocean/actions/runs/45886641958): passed UID/GID, all five capability sets, NNP, TCP, subprocess, asyncio, alternate working directory, online exception and subsequent offline restoration.
- Wrapper experiments failed Bash syntax checks on the remote runner and are superseded; they are not recommended.

## Boundaries

The default applies to run steps, not arbitrary uses actions, explicit shell overrides, other workflows, or the runner control plane. It is a defense against accidental direct network access, not a complete adversarial sandbox: filesystem Unix sockets, inherited descriptors, access to runner files and credentials, nested user namespaces and indirect services need separate controls. A new network namespace has no normal external network route; it does not prohibit socket creation. External IPv6 was not reachable in the baseline. Runner images may change; validate before rollout. Keep deployment in a separate least-privilege job where feasible. Do not use global Linux-only defaults for jobs on Windows/macOS.

## Rollout

1. Audit each workflow for run steps needing network and explicit shell overrides.
2. Put dependency installation and setup in explicit online steps; prefetch build backends and tools.
3. Apply the default to the Linux job/workflow and verify real build/test results.
4. For untrusted third-party actions use separate controls; do not claim that default run shell blocks their network.
5. Require successful CI, avoid silent fallback and preserve runner logs/artifacts.

The workflow-level multi-job and Bash failure-propagation extension is committed for validation; its result must be checked separately.
