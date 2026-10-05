# -*- coding: utf-8 -*-
"""Host metrics.

Cost budget: every function here must stay under ~1 ms. We read /proc and
/sys/fs/cgroup directly rather than calling psutil.cpu_percent(interval=1),
which BLOCKS the worker for a full second -- the single most common way a
health dashboard takes a server down.

Container awareness: when Odoo runs under Docker/k8s, the host figures are
misleading (a 4 GB container on a 64 GB host reports "6% RAM used" while Odoo
is being OOM-killed). We prefer cgroup limits whenever they are present.
"""

import logging
import os
import time

_logger = logging.getLogger(__name__)

# Per-process previous CPU snapshots for delta sampling, keyed by source.
_CPU_PREV = {}

# cgroup v1 uses this sentinel for "no limit".
_V1_UNLIMITED = 0x7FFFFFFFFFFFF000


def _read(path):
    try:
        with open(path, "r") as fh:
            return fh.read().strip()
    except (OSError, IOError):
        return None


def _read_int(path):
    raw = _read(path)
    if raw is None or raw == "max":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _cgroup_cpu_usage_usec():
    """Cumulative CPU time consumed by THIS cgroup, in microseconds."""
    # v2: cpu.stat carries usage_usec
    raw = _read("/sys/fs/cgroup/cpu.stat")
    if raw:
        for row in raw.splitlines():
            if row.startswith("usage_usec "):
                try:
                    return int(row.split()[1])
                except (ValueError, IndexError):
                    break
    # v1: cpuacct.usage is nanoseconds
    nanos = _read_int("/sys/fs/cgroup/cpuacct/cpuacct.usage")
    if nanos is not None:
        return nanos // 1000
    return None


def _host_cpu_percent():
    """Host-wide CPU from /proc/stat. Used when no cgroup quota applies."""
    line = None
    try:
        with open("/proc/stat", "r") as fh:
            line = fh.readline()
    except (OSError, IOError):
        return None
    if not line or not line.startswith("cpu "):
        return None

    fields = [int(x) for x in line.split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
    total = sum(fields)

    prev = _CPU_PREV.get("host")
    _CPU_PREV["host"] = (total, idle)
    if prev is None:
        return None

    d_total = total - prev[0]
    d_idle = idle - prev[1]
    if d_total <= 0:
        return None
    return round(100.0 * (d_total - d_idle) / d_total, 1)


def _cgroup_cpu_percent(cores):
    """CPU consumed by this container as a share of its own quota.

    Without this, a 2-core container on a 64-core host reports the HOST's
    utilisation -- so Odoo can be pinned at its quota while the dashboard
    cheerfully shows 4%. This is the number that actually matters when the
    workload is containerised.
    """
    usage = _cgroup_cpu_usage_usec()
    if usage is None or not cores:
        return None
    now = time.monotonic()

    prev = _CPU_PREV.get("cgroup")
    _CPU_PREV["cgroup"] = (usage, now)
    if prev is None:
        return None

    d_usage = usage - prev[0]
    d_wall = (now - prev[1]) * 1_000_000  # to microseconds
    if d_wall <= 0 or d_usage < 0:
        return None
    return round(min(100.0, 100.0 * d_usage / (d_wall * cores)), 1)


def cpu_percent():
    """Delta CPU since this worker's previous call. Non-blocking.

    Prefers the cgroup figure whenever a CPU quota is in force, because that
    is the ceiling Odoo will actually hit. Falls back to host-wide /proc/stat.

    Returns None on the first call in a worker -- the UI shows a dash rather
    than a fake 0%.
    """
    cores, _physical, capped = cpu_allowance()
    if capped:
        value = _cgroup_cpu_percent(cores)
        if value is not None:
            return value
    return _host_cpu_percent()


_ALLOWANCE = {}


def cpu_allowance():
    """Effective core count: cgroup quota if capped, else physical cores.

    Memoised -- this cannot change without restarting the container, and
    cpu_percent() consults it on every sample.
    """
    if "v" in _ALLOWANCE:
        return _ALLOWANCE["v"]
    _ALLOWANCE["v"] = _detect_allowance()
    return _ALLOWANCE["v"]


def _detect_allowance():
    """Read the effective core allowance from the OS.

    Named `_detect_` rather than `_compute_`: this is a plain module-level
    function reading /sys, not an Odoo compute method, and the `_compute_`
    prefix on a non-field function is misleading to both readers and static
    analysis.
    """
    physical = os.cpu_count() or 1

    # cgroup v2: "quota period" or "max period"
    raw = _read("/sys/fs/cgroup/cpu.max")
    if raw:
        parts = raw.split()
        if len(parts) == 2 and parts[0] != "max":
            try:
                return round(int(parts[0]) / int(parts[1]), 2), physical, True
            except (ValueError, ZeroDivisionError):
                pass

    # cgroup v1
    quota = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota and period and quota > 0:
        return round(quota / period, 2), physical, True

    return physical, physical, False


def _cgroup_memory():
    """(used_bytes, limit_bytes) from cgroup, or None."""
    # v2
    limit = _read_int("/sys/fs/cgroup/memory.max")
    current = _read_int("/sys/fs/cgroup/memory.current")
    if limit and current:
        inactive_file = 0
        stat = _read("/sys/fs/cgroup/memory.stat") or ""
        for row in stat.splitlines():
            if row.startswith("inactive_file "):
                try:
                    inactive_file = int(row.split()[1])
                except (ValueError, IndexError):
                    inactive_file = 0
                break
        return max(current - inactive_file, 0), limit

    # v1
    limit = _read_int("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    current = _read_int("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if limit and current and limit < _V1_UNLIMITED:
        inactive_file = 0
        stat = _read("/sys/fs/cgroup/memory/memory.stat") or ""
        for row in stat.splitlines():
            if row.startswith("total_inactive_file "):
                try:
                    inactive_file = int(row.split()[1])
                except (ValueError, IndexError):
                    inactive_file = 0
                break
        return max(current - inactive_file, 0), limit

    return None


def _host_memory():
    info = {}
    try:
        with open("/proc/meminfo", "r") as fh:
            for row in fh:
                key, _, rest = row.partition(":")
                info[key] = int(rest.split()[0]) * 1024
    except (OSError, IOError, ValueError, IndexError):
        return None
    total = info.get("MemTotal")
    available = info.get("MemAvailable")
    if not total:
        return None
    if available is None:
        available = info.get("MemFree", 0) + info.get("Cached", 0)
    return total - available, total


def memory():
    """Returns dict with used/limit and whether the limit is a container cap."""
    cg = _cgroup_memory()
    containerised = cg is not None
    values = cg or _host_memory()
    if not values:
        return None
    used, limit = values

    swap_used = swap_total = None
    try:
        swap = {}
        with open("/proc/meminfo", "r") as fh:
            for row in fh:
                key, _, rest = row.partition(":")
                if key in ("SwapTotal", "SwapFree"):
                    swap[key] = int(rest.split()[0]) * 1024
        swap_total = swap.get("SwapTotal", 0)
        swap_used = swap_total - swap.get("SwapFree", 0)
    except (OSError, IOError, ValueError, IndexError):
        swap_used = swap_total = None

    return {
        "used": used,
        "limit": limit,
        "percent": round(100.0 * used / limit, 1) if limit else None,
        "containerised": containerised,
        "swap_used": swap_used,
        "swap_total": swap_total,
    }


def load_average():
    try:
        one, five, fifteen = os.getloadavg()
    except (OSError, AttributeError):
        return None
    return {"1m": round(one, 2), "5m": round(five, 2), "15m": round(fifteen, 2)}


def disk(paths):
    """statvfs on the given mount points. Cheap -- one syscall each.

    Deliberately NOT a recursive size walk. Filestore byte counts are a cron
    job, not a live metric.
    """
    out = []
    seen = set()
    for path in paths:
        if not path:
            continue
        try:
            stat = os.statvfs(path)
        except (OSError, IOError):
            continue
        key = (stat.f_fsid, stat.f_blocks)
        if key in seen:
            continue
        seen.add(key)
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        if not total:
            continue
        out.append({
            "path": path,
            "total": total,
            "used": total - free,
            "free": free,
            "percent": round(100.0 * (total - free) / total, 1),
        })
    return out


def uptime_seconds():
    raw = _read("/proc/uptime")
    if not raw:
        return None
    try:
        return int(float(raw.split()[0]))
    except (ValueError, IndexError):
        return None


def prime():
    """Seed both CPU deltas so the first real poll returns a number."""
    try:
        cpu_allowance()
        _host_cpu_percent()
        _cgroup_cpu_percent(cpu_allowance()[0])
    except Exception:
        _logger.debug("Could not prime CPU sampler", exc_info=True)
