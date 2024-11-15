from findingmodelforge import hello, __version__

def test_version():
    assert __version__

def test_hello():
    got = hello()
    expected = "Hello from findingmodelforge!"
    assert got == expected
