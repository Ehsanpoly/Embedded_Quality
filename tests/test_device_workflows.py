import pytest

from eqv.device import DeviceError


@pytest.mark.hil
@pytest.mark.release_gate
def test_device_ping_and_measurements_are_observable(device, artifacts_dir):
    assert device.ping() is True
    values = {
        "pv_power_kw": device.read_measurement("pv_power_kw"),
        "ev_power_kw": device.read_measurement("ev_power_kw"),
        "grid_power_kw": device.read_measurement("grid_power_kw"),
        "battery_soc_percent": device.read_measurement("battery_soc_percent"),
    }
    assert values["pv_power_kw"] > 0
    assert 0 <= values["battery_soc_percent"] <= 100


@pytest.mark.hil
@pytest.mark.release_gate
def test_v2h_mode_is_blocked_when_soc_is_too_low(hil_transport, device):
    hil_transport.battery_soc_percent = 15.0
    with pytest.raises(DeviceError, match="safety interlock"):
        device.set_mode("V2H_BACKUP")


@pytest.mark.hil
@pytest.mark.release_gate
def test_ev_charge_mode_acknowledged(device):
    assert device.set_mode("EV_CHARGE") == "EV_CHARGE"


@pytest.mark.cloud
@pytest.mark.release_gate
def test_device_to_cloud_telemetry_round_trip(device, cloud):
    payload = {
        "cloud_status": device.cloud_status(),
        "ota_status": device.ota_status(),
        "pv_power_kw": round(device.read_measurement("pv_power_kw"), 2),
        "battery_soc_percent": round(device.read_measurement("battery_soc_percent"), 2),
    }
    ack = cloud.publish_telemetry("ARA-SIM-0001", payload)
    assert ack["accepted"] is True
    assert cloud.last_payload()["cloud_status"] == "CONNECTED"
