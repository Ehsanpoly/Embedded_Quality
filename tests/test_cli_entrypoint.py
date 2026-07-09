from eqv.cli import main


def test_cli_smoke_writes_report(tmp_path):
    output = tmp_path / "smoke.json"
    assert main(["smoke", "--output", str(output)]) == 0
    assert output.exists()
