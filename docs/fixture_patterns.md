# Advanced pytest fixture patterns for embedded validation

This repo intentionally uses pytest fixtures as **bench orchestration primitives**, not only as test helpers. In an embedded-quality environment, a fixture often represents a device bench, a transport, a firmware diagnostic client, a cloud test double, a power/relay state, or a repeatable fault injection setup.

## Where the fixture patterns live

```text
tests/conftest.py                 shared fixture definitions
tests/test_advanced_fixtures.py   examples that consume advanced fixtures
artifacts/fixture_lifecycle.jsonl autouse setup/teardown lifecycle evidence
```

## 1. Parametrized fixtures

A parametrized fixture runs the **same test multiple times** with different inputs. This is useful when the validation logic is identical, but the embedded product state changes.

In `tests/conftest.py`:

```python
@pytest.fixture(params=[...], ids=lambda scenario: scenario.name)
def energy_scenario(request):
    return request.param
```

The test using it:

```python
def test_parametrized_energy_scenarios_run_same_test_against_multiple_profiles(
    device_factory,
    energy_scenario,
):
    ...
```

Pytest expands that one test into multiple cases such as:

```text
sunny_self_consumption
evening_ev_charge
backup_ready_high_soc
```

For an embedded home-energy product, this pattern can represent different EV/PV/BESS/grid conditions without copying the same test body.

A second parametrized fixture is `memory_fault_case`, which runs one memory/NVM test across healthy and faulty cases:

```text
healthy_nvm
crc_mismatch_release_blocker
scratch_stuck_bit_release_blocker
```

## 2. Factory fixtures with dynamic arguments

A factory fixture returns a function. The test can call that function with custom arguments to build exactly the bench state it needs.

In `tests/conftest.py`:

```python
@pytest.fixture
def device_factory():
    def _factory(**transport_overrides):
        transport = FakeHilTransport(**transport_overrides)
        return transport, HomeEnergyStationClient(transport)
    return _factory
```

Example use:

```python
transport, device = device_factory(
    battery_soc_percent=12.5,
    pv_power_kw=0.1,
)
```

This is valuable when a test needs a specific state, such as low SOC, schema mismatch, cloud disconnected, high NVM wear count, or injected memory fault.

The repo also includes `memory_client_factory`, which builds a `MemoryDiagnosticClient` dynamically:

```python
_, memory = memory_client_factory(
    nvm_schema_version=2,
    expected_nvm_schema_version=3,
)
```

## 3. Autouse fixtures

An autouse fixture executes automatically for every test, even when the test does not list it in the function signature.

In `tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def record_fixture_lifecycle(request, artifacts_dir):
    append_jsonl(... setup event ...)
    yield
    append_jsonl(... teardown event ...)
```

This produces:

```text
artifacts/fixture_lifecycle.jsonl
```

This is useful in embedded quality because bench hygiene should be automatic. Examples:

- open and close power relay control safely;
- clear fault injection state;
- collect logs after each test;
- record device serial and firmware version;
- reset bench state after failures;
- capture setup/teardown timing.

In this showcase, the autouse fixture records setup and teardown evidence without changing existing tests.

## Fixture setup and teardown mechanics

A fixture can use `yield` to split setup and teardown:

```python
@pytest.fixture
def bench_resource():
    # setup
    resource = open_resource()
    yield resource
    # teardown
    resource.close()
```

Execution order:

```text
fixture setup
  ↓
test function
  ↓
fixture teardown
```

If several fixtures are used, pytest resolves dependencies first. For example:

```text
artifacts_dir setup
  ↓
record_fixture_lifecycle setup
  ↓
hil_transport setup
  ↓
device setup
  ↓
test body
  ↓
device teardown, if defined
  ↓
hil_transport teardown, if defined
  ↓
record_fixture_lifecycle teardown
```

## Fixture lifecycle scopes

Pytest fixtures can have different scopes:

| Scope | Created | Typical embedded-quality use |
|---|---|---|
| `function` | once per test | clean device state, fault injection, per-test logs |
| `class` | once per test class | grouped scenario state |
| `module` | once per test file | shared simulator or loaded fixture data |
| `package` | once per package | larger subsystem environment |
| `session` | once per pytest run | run metadata, expensive tool discovery, lab inventory |

This repo includes `validation_session_metadata` as a `session` fixture. It demonstrates run-level metadata that does not need to be rebuilt for each test.

## Why these patterns matter for embedded quality

Advanced fixtures make tests faster, cleaner, and more scalable:

- **Parametrized fixtures** increase coverage without duplicated tests.
- **Factory fixtures** create precise device/bench states on demand.
- **Autouse fixtures** enforce setup/teardown hygiene automatically.
- **Lifecycle scopes** control speed versus isolation.

For real hardware, the same ideas can control USB serial ports, CAN adapters, relay boards, cloud sandboxes, OTA servers, and memory diagnostic states.
