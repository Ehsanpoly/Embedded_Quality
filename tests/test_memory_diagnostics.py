import pytest

from eqv.memory_diagnostics import MemoryDiagnosticClient


@pytest.mark.release_gate
def test_ram_quick_check_passes(device):
    memory = MemoryDiagnosticClient(device)
    report = memory.run_ram_quick_check()
    assert report.passed is True
    assert report.details["tested_bytes"] > 0
    assert report.details["region"] == "diagnostic_reserved_ram"


@pytest.mark.release_gate
def test_nvm_crc_mismatch_blocks_release(device):
    memory = MemoryDiagnosticClient(device)
    memory.inject_fault("nvm_crc_mismatch")

    report = memory.verify_nvm_crc()

    assert report.passed is False
    assert report.is_release_blocker is True
    assert report.details["expected_crc"] != report.details["actual_crc"]


@pytest.mark.release_gate
def test_eeprom_scratch_write_readback(device):
    memory = MemoryDiagnosticClient(device)
    report = memory.scratch_write_readback(key="bench_counter", value=7)
    assert report.passed is True
    assert report.details["written"] == 7
    assert report.details["readback"] == 7


@pytest.mark.release_gate
def test_factory_region_is_read_only(device):
    memory = MemoryDiagnosticClient(device)
    report = memory.verify_factory_region_locked()
    assert report.passed is True
    assert report.details["factory_region_locked"] is True
    assert report.details["attempted_write_blocked"] is True
