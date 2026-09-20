import pytest
from excelpilot.bridge.file import FileBridge
from excelpilot.bridge.models import RangeRef


@pytest.mark.asyncio
async def test_file_bridge_read_and_write(tmp_path):
    wb_file = tmp_path / "test_book.xlsx"
    bridge = FileBridge(file_path=str(wb_file))

    # Test sheet list and add sheet
    sheets = await bridge.list_sheets()
    assert len(sheets) >= 1

    new_sheet = await bridge.add_sheet(name="Data")
    assert new_sheet.name == "Data"

    # Test write values
    ref = RangeRef(sheet="Data", address="A1:B2")
    write_res = await bridge.write(ref, values=[[10, 20], [30, 40]])
    assert write_res.success is True
    assert write_res.cells_modified == 4

    # Test read values
    read_res = await bridge.read(ref, values=True)
    assert read_res.values == [[10, 20], [30, 40]]

    # Test clear
    clear_ok = await bridge.clear(RangeRef(sheet="Data", address="A1:A1"))
    assert clear_ok is True
    read_cleared = await bridge.read(ref, values=True)
    assert read_cleared.values[0][0] is None

    # Test create table
    table_name = await bridge.create_table(
        RangeRef(sheet="Data", address="B1:B2"), name="TestTable"
    )
    assert table_name == "TestTable"
    tables = await bridge.list_tables("Data")
    assert any(t["name"] == "TestTable" for t in tables)
