import inspect


def test_main_module_imports():
    import main  # noqa: F401


def test_main_is_async():
    from main import main

    assert inspect.iscoroutinefunction(main)
