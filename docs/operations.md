# Operations

## Configuration

The default settings path is resolved relative to `inventory_report.py`, not the
current working directory. Output paths are relative to the working directory.
Use `--config`, `--bucket`, `--prefix`, and `--output` to override a run.
An empty prefix selects the entire bucket. Region must match the target bucket.

The utility uses an explicit access-key pair from `[aws]`. Both fields are
required in live mode. Neither value is printed by the application.

## Execution

Live reports use the S3 `list_objects_v2` paginator. No object-read, upload,
delete, IAM, or bucket-creation calls are made by the utility. Request retries
are bounded to three total attempts; connection and read timeouts are five and
thirty seconds respectively.

Listing permissions are still required even when no object bodies are read.
A credential that cannot list the target bucket will not produce a usable live
report. A failed listing can leave a partial output file; check the process exit
status before consuming the result. Rerun to replace incomplete output.

## CSV format

| Column | Meaning |
| --- | --- |
| bucket | Bucket selected for the run |
| key | Object key, preserved verbatim |
| size_bytes | Object size in bytes |
| last_modified | ISO timestamp when supplied by AWS |
| storage_class | Storage class, defaulting to STANDARD when absent |

CSV quoting handles commas and newlines in object keys. Keys are preserved as
text; treat the report as untrusted data when importing into spreadsheet tools.
The listing covers current objects, not all versions or delete markers. It is
not a transactionally consistent snapshot if the bucket changes during a run.

## Scheduling

The repository does not install a schedule. If running from cron, use absolute
paths for the interpreter, script, settings, and output; capture the exit status
and stderr. Keep report retention and notification handling outside this tool.
