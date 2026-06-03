from datetime import date

from app.services.expense_service import parse_natural_search_filters


def test_parse_natural_search_filters():
    filters = parse_natural_search_filters("Show food expenses from May at Pizza Hut")

    assert filters["category"] == "Food"
    assert filters["vendor"] == "Pizza Hut"
    assert filters["date_from"] == date(date.today().year, 5, 1)
    assert filters["date_to"].day in (30, 31)
    assert filters["date_to"].month == 5
