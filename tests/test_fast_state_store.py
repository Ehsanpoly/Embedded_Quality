from eqv.fast_state_store import FastStateStore


def test_cached_crc_skips_expensive_nvm_scan():
    store = FastStateStore()
    store.set("memory.nvm.crc", "0x91AF")
    assert store.has_changed("memory.nvm.crc", "0x91AF") is False
    assert store.has_changed("memory.nvm.crc", "0xDEAD") is True


def test_snapshot_diff_reports_changed_keys():
    before = {"memory.nvm.crc": "0x91AF", "cloud.heartbeat": "CONNECTED"}
    after = {"memory.nvm.crc": "0xDEAD", "cloud.heartbeat": "CONNECTED"}
    diff = FastStateStore.diff(before, after)
    assert diff == {"memory.nvm.crc": {"before": "0x91AF", "after": "0xDEAD"}}


def test_stream_keeps_telemetry_events():
    store = FastStateStore()
    store.append_stream("telemetry", {"pv_power_kw": 4.2})
    store.append_stream("telemetry", {"pv_power_kw": 4.5})
    assert len(store.stream("telemetry")) == 2
    assert "stream:telemetry" in store.dirty_keys()
