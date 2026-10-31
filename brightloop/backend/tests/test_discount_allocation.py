from app.services.discounts import _allocate_discount


def make_lines(amounts: list[int]) -> list[dict]:
    return [
        {
            "line_subtotal": amount,
            "discount_amount": 0,
        }
        for amount in amounts
    ]


def test_discount_is_allocated_proportionally() -> None:
    lines = make_lines([100, 300])

    _allocate_discount(lines, 100, 400)

    assert [line["discount_amount"] for line in lines] == [25, 75]


def test_rounding_remainder_is_allocated() -> None:
    lines = make_lines([1, 1, 1])

    _allocate_discount(lines, 2, 3)

    assert [line["discount_amount"] for line in lines] == [1, 1, 0]
    assert sum(line["discount_amount"] for line in lines) == 2


def test_discount_never_exceeds_line_value() -> None:
    lines = make_lines([100, 100])

    _allocate_discount(lines, 200, 200)

    assert [line["discount_amount"] for line in lines] == [100, 100]


def test_zero_discount_changes_nothing() -> None:
    lines = make_lines([100, 200])

    _allocate_discount(lines, 0, 300)

    assert [line["discount_amount"] for line in lines] == [0, 0]


def test_existing_discount_is_respected() -> None:
    lines = [
        {"line_subtotal": 100, "discount_amount": 20},
        {"line_subtotal": 300, "discount_amount": 0},
    ]

    _allocate_discount(lines, 80, 380)

    assert [line["discount_amount"] for line in lines] == [37, 63]
    assert sum(line["discount_amount"] for line in lines) == 100
