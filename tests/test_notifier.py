from bot.services.notifier import format_order_message


def test_format_order_message(sample_order):
    msg = format_order_message(sample_order)

    assert "#1" in msg
    assert "Ali" in msg
    assert "+998901234567" in msg
    assert "Toshkent" in msg
    assert "Qurut" in msg
    assert "Non" in msg
    assert "50,000" in msg
    assert "<b>" in msg
