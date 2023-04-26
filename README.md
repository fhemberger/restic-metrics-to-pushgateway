# Restic snapshot metrics to Prometheus Pushgateway

Simple script to push metrics of the latest [restic](https://github.com/restic/restic) backup snapshot to [Prometheus](https://prometheus.io/) [Pushgateway](https://github.com/prometheus/pushgateway).

There are also Prometheus exporters for restic, but the underlying `restic stats` command they use comes with high CPU and memory consumption ([#2126](https://github.com/restic/restic/issues/2126)). Since I'm only interested in the last snapshot for alerting rather than creating detailed dashboards, regularly pushing the latest snapshot infos seemed to be the easier route.


## Usage

The scripts expects **[environment variables](https://restic.readthedocs.io/en/stable/040_backup.html#environment-variables)** to access the restic repository, and the Pushgateway URL as parameter:

```
usage: restic_metrics_to_pushgateway.py [-h] [--loglevel] --pushgateway_url URL [--tls_skip_verify]

Send metrics of latest restic snapshot to Prometheus Pushgateway.

options:
  -h, --help            show this help message and exit
  --loglevel LEVEL      log level ({CRITICAL,ERROR,WARNING,INFO,DEBUG}, default: INFO)
  --pushgateway_url URL Prometheus Pushgateway URL
                        (e.g. "http://pushgateway.example.org:9091/metrics/job/some_job/instance/some_instance")
  --tls_skip_verify     Skip TLS certificate verification.
```


## Example Prometheus alerting rule

```yaml
groups:
  - name: restic
    rules:
      - alert: ResticOutdatedBackup
        annotations:
          summary: Restic backup on {{ $labels.hostname }} is outdated
          description: |
            Restic backup on {{ $labels.hostname }} is outdated:
            Last backup: {{ $value | humanizeTimestamp }}
            User: {{ $labels.username }}
            Paths: {{ $labels.paths }}
            Tags: {{ $labels.tags }}
        # 86400 = 24 hours
        expr: time() - restic_last_snapshot{hostname!="ares"} > 86400
        for: 24h
        labels:
          severity: critical
```


## License

[MIT](LICENSE)
