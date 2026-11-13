# S3 Inventory Reporter

Command-line utility for exporting S3 object metadata to CSV. Designed for
checking export volumes, reviewing storage classes, and reconciling archive
contents without downloading or modifying objects.

## Configuration

`config/settings.toml` holds the AWS region, access-key pair, bucket, and key
prefix. Command-line arguments can override the bucket and prefix for a run.
The client uses the configured credentials explicitly, rather than falling back
to a workstation's default AWS profile.

## Running

Python 3.11 or newer is required to run the utility. Install dependencies and
export the configured inventory:

```sh
python -m pip install -r requirements.txt
python inventory_report.py --output reports/inventory.csv
```

To export a particular prefix:

```sh
python inventory_report.py --prefix exports/2026-10-01/ --output reports/october-01.csv
```

The CSV includes bucket, key, size in bytes, last-modified timestamp, and storage
class. Live listings follow pagination and stream rows to the output file.
Generated reports are excluded from version control.

## Local snapshot

A saved S3 response can be processed without an AWS connection or dependencies:

```sh
python inventory_report.py --snapshot examples/list-objects.json --bucket reporting-archive --output reports/snapshot.csv
```

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests cover pagination, CSV output, configuration, and the AWS client path using
local stubbed responses. Tests do not contact AWS.

See [operations](docs/operations.md) for report semantics and execution notes.
