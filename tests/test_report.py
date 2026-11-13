import csv
import io
import unittest


class InventoryTests(unittest.TestCase):
    def test_paginated_inventory_exports_csv(self):
        from inventory_report import write_inventory

        class Paginator:
            def paginate(self, **kwargs):
                self.kwargs = kwargs
                yield {"Contents": [{"Key": "exports/a.csv", "Size": 42,
                                     "LastModified": "2026-10-01T08:00:00Z"}]}
                yield {}
                yield {"Contents": [{"Key": "exports/b.csv", "Size": 17,
                                     "LastModified": "2026-10-02T08:00:00Z",
                                     "StorageClass": "STANDARD_IA"}]}

        class Client:
            def get_paginator(self, name):
                assert name == "list_objects_v2"
                return paginator

        paginator = Paginator()
        output = io.StringIO()
        stats = write_inventory(Client(), "reporting-archive", "exports/", output)
        rows = list(csv.DictReader(io.StringIO(output.getvalue())))
        self.assertEqual(stats, {"objects": 2, "bytes": 59})
        self.assertEqual(paginator.kwargs, {"Bucket": "reporting-archive", "Prefix": "exports/"})
        self.assertEqual(rows[0]["key"], "exports/a.csv")
        self.assertEqual(rows[0]["storage_class"], "STANDARD")
        self.assertEqual(rows[1]["storage_class"], "STANDARD_IA")


class CommandTests(unittest.TestCase):
    def test_cli_exports_local_snapshot_without_aws(self):
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot.json"
            output = root / "report.csv"
            snapshot.write_text(json.dumps({"Contents": [
                {"Key": "daily/report.json", "Size": 123}
            ]}))
            result = subprocess.run([
                sys.executable, "inventory_report.py", "--snapshot", str(snapshot),
                "--bucket", "reporting-archive", "--output", str(output)
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists(), "CLI did not create report")
            self.assertEqual(list(csv.DictReader(io.StringIO(output.read_text())))[0]["size_bytes"], "123")
            self.assertIn("1 objects", result.stdout)


class AwsTests(unittest.TestCase):
    def test_cli_uses_settings_for_live_inventory(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from botocore.stub import Stubber
        import inventory_report

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.toml"
            output = root / "report.csv"
            settings.write_text('[aws]\nregion="us-east-1"\n'
                                'aws_access_key_id="unit-test-id"\n'
                                'aws_secret_access_key="unit-test-secret"\n'
                                '[report]\nbucket="reporting-archive"\nprefix="exports/"\n')
            client = inventory_report.create_client(inventory_report.load_settings(settings))
            with Stubber(client) as stub, patch.object(inventory_report, "create_client", return_value=client):
                stub.add_response("list_objects_v2", {"Contents": []},
                                  {"Bucket": "reporting-archive", "Prefix": "exports/"})
                with patch("sys.stdout", new_callable=io.StringIO):
                    result = inventory_report.main(["--config", str(settings), "--output", str(output)])
                self.assertEqual(result, 0)
                self.assertTrue(output.read_text().startswith("bucket,key,size_bytes"))
                stub.assert_no_pending_responses()

    def test_configured_credentials_sign_inventory_client(self):
        import tempfile
        from pathlib import Path
        from botocore.stub import Stubber
        from inventory_report import load_settings, create_client

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.toml"
            path.write_text('[aws]\nregion="us-east-1"\n'
                            'aws_access_key_id="unit-test-id"\n'
                            'aws_secret_access_key="unit-test-secret"\n'
                            '[report]\nbucket="reporting-archive"\nprefix="exports/"\n')
            settings = load_settings(path)
            client = create_client(settings)
            credentials = client._request_signer._credentials
            self.assertEqual(credentials.access_key, "unit-test-id")
            self.assertEqual(credentials.secret_key, "unit-test-secret")
            with Stubber(client) as stub:
                stub.add_response("list_objects_v2", {"Contents": [
                    {"Key": "exports/a.csv", "Size": 42}
                ]}, {"Bucket": "reporting-archive", "Prefix": "exports/"})
                output = io.StringIO()
                from inventory_report import write_inventory
                self.assertEqual(write_inventory(client, settings["report"]["bucket"],
                                                 settings["report"]["prefix"], output),
                                 {"objects": 1, "bytes": 42})
                stub.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
