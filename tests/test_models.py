from chrono_des_vignes.models import User, get_column_max_length, get_html_from_markdown


def test_get_html_from_markdown_escapes_html_and_renders_markdown():
    html = get_html_from_markdown("# Bonjour <script>alert('x')</script>")
    assert "<h1>Bonjour" in html
    assert "&lt;script&gt;" in html
    assert "<script>" not in html


def test_get_column_max_length_returns_string_length_for_string_column():
    assert get_column_max_length(User, "name") == 40


def test_get_column_max_length_returns_large_value_for_non_string_column():
    assert get_column_max_length(User, "id") == 2147483647
