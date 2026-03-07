import inspect


def test_cli_module_imports():
    import patchwork.cli  # noqa: F401


def test_main_is_async():
    from patchwork.cli import main

    assert inspect.iscoroutinefunction(main)
