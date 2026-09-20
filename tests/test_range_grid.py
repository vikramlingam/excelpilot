from excelpilot.tools.ranges import as_grid


def test_as_grid_scalar_and_ragged():
    assert as_grid(42) == [[42]]
    assert as_grid(["a", "b", "c"]) == [["a", "b", "c"]]
    assert as_grid([["x"]]) == [["x"]]
    assert as_grid([[1, 2], [3]]) == [[1, 2], [3, None]]
    assert as_grid(None) == [[""]]
    assert as_grid([]) == [[""]]
