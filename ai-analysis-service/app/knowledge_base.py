"""
Static knowledge base mapping common alert patterns to root causes and solutions.

Each entry is a known SRE pattern accumulated from operational experience.
The NLP engine uses these as reference documents for similarity search.
"""

KNOWN_PATTERNS = [
    # ── CPU / Compute ────────────────────────────────────────
    {
        "pattern": "high cpu usage cpu utilization above threshold",
        "service_hint": None,
        "root_cause": "Runaway process, inefficient query, or traffic spike consuming excessive CPU cycles.",
        "solution": (
            "1. Identify the top-consuming process with `top` or `htop`.\n"
            "2. Check recent deployments for regressions.\n"
            "3. Scale horizontally if traffic-driven, or optimize hot code paths.\n"
            "4. Consider enabling CPU throttling or autoscaling policies."
        ),
        "tags": ["cpu", "compute", "performance"],
    },
    {
        "pattern": "cpu throttling detected container cpu limit exceeded cgroup",
        "service_hint": None,
        "root_cause": "Container CPU limit is too low for the current workload, causing kernel-level throttling.",
        "solution": (
            "1. Review container CPU limits vs actual usage in Grafana.\n"
            "2. Increase the CPU limit in the deployment spec.\n"
            "3. Profile the application to reduce CPU-intensive operations.\n"
            "4. Distribute work across more replicas."
        ),
        "tags": ["cpu", "container", "throttling"],
    },
    # ── Memory ───────────────────────────────────────────────
    {
        "pattern": "high memory usage memory utilization above threshold out of memory oom",
        "service_hint": None,
        "root_cause": "Memory leak, large cache growth, or insufficient memory allocation for the workload.",
        "solution": (
            "1. Check for memory leaks using profiling tools (e.g. `valgrind`, `py-spy`).\n"
            "2. Review recent code changes for unbounded caches or data structures.\n"
            "3. Increase memory limits or add more nodes.\n"
            "4. Restart the affected pod/container as immediate mitigation."
        ),
        "tags": ["memory", "oom", "leak"],
    },
    {
        "pattern": "oom killed out of memory killed process",
        "service_hint": None,
        "root_cause": "The Linux OOM killer terminated the process because the system ran out of available memory.",
        "solution": (
            "1. Increase memory limits for the container / VM.\n"
            "2. Investigate the process for memory leaks.\n"
            "3. Add swap space as a temporary buffer.\n"
            "4. Implement memory-aware health checks to restart before OOM."
        ),
        "tags": ["memory", "oom", "kernel"],
    },
    # ── Disk ─────────────────────────────────────────────────
    {
        "pattern": "disk space low disk usage above threshold filesystem full",
        "service_hint": None,
        "root_cause": "Log accumulation, temp files, or data growth has exhausted available disk space.",
        "solution": (
            "1. Identify large files: `du -sh /* | sort -rh | head`.\n"
            "2. Rotate or compress old logs.\n"
            "3. Clean temp files and unused Docker images.\n"
            "4. Expand the volume or add a larger disk."
        ),
        "tags": ["disk", "storage", "filesystem"],
    },
    # ── Network / Connectivity ───────────────────────────────
    {
        "pattern": "connection timeout request timeout upstream timeout gateway timeout",
        "service_hint": None,
        "root_cause": "Downstream service is overloaded, unreachable, or taking too long to respond.",
        "solution": (
            "1. Check health of the downstream service.\n"
            "2. Review network policies and firewall rules.\n"
            "3. Increase timeout thresholds if the service is legitimately slow.\n"
            "4. Add circuit breakers and retry logic with exponential backoff."
        ),
        "tags": ["network", "timeout", "connectivity"],
    },
    {
        "pattern": "connection refused port unreachable service unavailable ECONNREFUSED",
        "service_hint": None,
        "root_cause": "Target service is not running, crashed, or the port is not exposed.",
        "solution": (
            "1. Verify the service is running: `docker ps` or `systemctl status`.\n"
            "2. Check if the correct port is exposed and mapped.\n"
            "3. Review recent restarts or crash loops in container logs.\n"
            "4. Check DNS resolution and service discovery configuration."
        ),
        "tags": ["network", "connection", "crash"],
    },
    {
        "pattern": "dns resolution failed dns lookup timeout name resolution",
        "service_hint": None,
        "root_cause": "DNS server is unreachable or misconfigured, preventing hostname resolution.",
        "solution": (
            "1. Test DNS with `nslookup` or `dig`.\n"
            "2. Check /etc/resolv.conf for correct nameservers.\n"
            "3. Restart DNS cache service (e.g. dnsmasq, CoreDNS).\n"
            "4. Verify network connectivity to the DNS server."
        ),
        "tags": ["dns", "network", "resolution"],
    },
    {
        "pattern": "high latency response time slow increased p99 p95",
        "service_hint": None,
        "root_cause": "Database query degradation, resource contention, or network congestion causing slow responses.",
        "solution": (
            "1. Check database slow query logs.\n"
            "2. Review CPU, memory, and I/O metrics of the service.\n"
            "3. Profile application code for hot paths.\n"
            "4. Check network latency between service components."
        ),
        "tags": ["latency", "performance", "slow"],
    },
    # ── Database ─────────────────────────────────────────────
    {
        "pattern": "database connection pool exhausted too many connections max connections",
        "service_hint": None,
        "root_cause": "Application is opening more DB connections than the pool supports, likely due to connection leaks.",
        "solution": (
            "1. Review connection pool settings (min/max connections).\n"
            "2. Check for connection leaks — ensure connections are returned to the pool.\n"
            "3. Increase `max_connections` in PostgreSQL config.\n"
            "4. Add PgBouncer as a connection pooler."
        ),
        "tags": ["database", "postgresql", "connection"],
    },
    {
        "pattern": "database replication lag replica behind primary secondary lag",
        "service_hint": None,
        "root_cause": "Write-heavy workload or network issues causing the replica to fall behind the primary.",
        "solution": (
            "1. Check replication status: `SELECT * FROM pg_stat_replication`.\n"
            "2. Reduce write load or batch heavy operations.\n"
            "3. Increase WAL sender bandwidth / resources.\n"
            "4. Consider switching reads to the primary temporarily."
        ),
        "tags": ["database", "replication", "lag"],
    },
    {
        "pattern": "slow query long running query lock contention deadlock database",
        "service_hint": None,
        "root_cause": "Unoptimized query, missing index, or lock contention blocking other transactions.",
        "solution": (
            "1. Identify the slow query via `pg_stat_activity` or slow query log.\n"
            "2. Run EXPLAIN ANALYZE on the query to find bottlenecks.\n"
            "3. Add appropriate indexes.\n"
            "4. Break large transactions into smaller batches."
        ),
        "tags": ["database", "query", "performance"],
    },
    # ── Application Errors ───────────────────────────────────
    {
        "pattern": "http 500 internal server error 5xx error rate increased",
        "service_hint": None,
        "root_cause": "Unhandled exception, misconfiguration, or dependency failure causing server errors.",
        "solution": (
            "1. Check application logs for the stack trace.\n"
            "2. Review recent deployments for breaking changes.\n"
            "3. Verify all environment variables and configuration.\n"
            "4. Check downstream dependency health.\n"
            "5. Roll back the last deployment if recently changed."
        ),
        "tags": ["http", "error", "500"],
    },
    {
        "pattern": "http 429 rate limited too many requests throttled",
        "service_hint": None,
        "root_cause": "Client or service is exceeding rate limits set by an API gateway or upstream provider.",
        "solution": (
            "1. Implement client-side rate limiting and backoff.\n"
            "2. Review if the rate limit configuration is too strict.\n"
            "3. Cache responses to reduce duplicate requests.\n"
            "4. Distribute load across multiple API keys if applicable."
        ),
        "tags": ["http", "rate-limit", "throttle"],
    },
    {
        "pattern": "crash loop restart backoff pod restarting container crash CrashLoopBackOff",
        "service_hint": None,
        "root_cause": "Application is crashing on startup due to misconfiguration, missing dependency, or OOM.",
        "solution": (
            "1. Check container logs: `docker logs <container>` or `kubectl logs`.\n"
            "2. Verify environment variables and secrets.\n"
            "3. Check if healthcheck is too aggressive.\n"
            "4. Review resource limits (memory/CPU) — may be too low.\n"
            "5. Test the image locally to reproduce."
        ),
        "tags": ["crash", "restart", "container"],
    },
    # ── SSL / TLS / Auth ─────────────────────────────────────
    {
        "pattern": "ssl certificate expired tls handshake failed certificate invalid",
        "service_hint": None,
        "root_cause": "TLS certificate has expired or is invalid, breaking secure connections.",
        "solution": (
            "1. Check certificate expiry: `openssl x509 -enddate -noout -in cert.pem`.\n"
            "2. Renew the certificate via your CA or Let's Encrypt.\n"
            "3. Restart the service to pick up the new cert.\n"
            "4. Set up auto-renewal with certbot or similar."
        ),
        "tags": ["ssl", "tls", "certificate"],
    },
    {
        "pattern": "authentication failed unauthorized 401 token expired invalid credentials",
        "service_hint": None,
        "root_cause": "Expired or invalid auth token, rotated credentials, or misconfigured auth provider.",
        "solution": (
            "1. Refresh or re-issue the authentication token.\n"
            "2. Verify credentials in secrets/environment config.\n"
            "3. Check if auth provider (OAuth, LDAP) is operational.\n"
            "4. Review token expiry settings."
        ),
        "tags": ["auth", "token", "security"],
    },
    # ── Kubernetes / Container Orchestration ─────────────────
    {
        "pattern": "pod pending insufficient resources unschedulable no nodes available",
        "service_hint": None,
        "root_cause": "Cluster lacks sufficient resources (CPU, memory) to schedule the pod.",
        "solution": (
            "1. Check node resource usage: `kubectl top nodes`.\n"
            "2. Scale up the node pool or add new nodes.\n"
            "3. Reduce resource requests if over-provisioned.\n"
            "4. Check for resource quotas limiting the namespace."
        ),
        "tags": ["kubernetes", "scheduling", "resources"],
    },
    {
        "pattern": "health check failed readiness probe liveness probe failed endpoint unhealthy",
        "service_hint": None,
        "root_cause": "Service health endpoint returning errors, possibly due to dependency failure or startup delay.",
        "solution": (
            "1. Check application logs at the time of the probe failure.\n"
            "2. Increase initialDelaySeconds if the app needs more startup time.\n"
            "3. Verify the health endpoint returns 200 when dependencies are healthy.\n"
            "4. Check downstream service connectivity."
        ),
        "tags": ["health", "probe", "kubernetes"],
    },
    # ── Queue / Messaging ────────────────────────────────────
    {
        "pattern": "queue depth growing message backlog consumer lag kafka rabbitmq",
        "service_hint": None,
        "root_cause": "Consumers cannot keep up with the message production rate.",
        "solution": (
            "1. Scale up consumer instances.\n"
            "2. Check consumer processing time for bottlenecks.\n"
            "3. Increase consumer batch size if applicable.\n"
            "4. Review for poison messages blocking the queue."
        ),
        "tags": ["queue", "messaging", "backlog"],
    },
]
