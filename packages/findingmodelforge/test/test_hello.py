from findingmodelforge import hello


def test_hello():
    got = hello()
    expected = "Hello from findingmodelforge!"
    assert got == expected
