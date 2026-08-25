from example_app.core.example import Money, add_money
from example_app.settings import get_settings


def test_add_money_is_exact():
    assert add_money(Money(cents=150), Money(cents=275)) == Money(cents=425)


def test_settings_reads_env(monkeypatch, fresh_settings):
    monkeypatch.setenv("APP_NAME", "from-env")
    assert get_settings().app_name == "from-env"


def test_golden_example(golden):
    golden("money_sum", add_money(Money(cents=1), Money(cents=2)).model_dump())
