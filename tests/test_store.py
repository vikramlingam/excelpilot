from excelpilot.store.db import Store


def test_snapshot_and_restore(tmp_path):
    db_file = tmp_path / "test_store.sqlite"
    test_store = Store(db_path=db_file)

    values = [[1, 2, "hello"], [4, 5, "world"]]
    formulas = [["=A1", None, None], [None, None, "=B2*2"]]

    snap_id = test_store.create_snapshot(
        session_id="test_sess",
        sheet="Sheet1",
        address="A1:C2",
        values=values,
        formulas=formulas,
    )
    assert snap_id.startswith("snap_")

    restored = test_store.get_snapshot(snap_id)
    assert restored is not None
    assert restored["sheet"] == "Sheet1"
    assert restored["values"] == values
    assert restored["formulas"] == formulas


def test_audit_and_cost_tracking(tmp_path):
    db_file = tmp_path / "test_audit.sqlite"
    test_store = Store(db_path=db_file)

    test_store.record_audit(
        session_id="sess_1",
        tool="range_write_values",
        args={"sheet": "Sheet1", "address": "A1"},
        outcome="approved",
        jev_backend="typesafe",
        jev_probs={"requested": 0.95},
    )

    test_store.record_cost("sess_1", 0.0025)
    daily = test_store.get_daily_cost()
    assert daily == 0.0025
