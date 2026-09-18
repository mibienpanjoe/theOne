from theone.naming import OUTPUT_TEMPLATE, output_template


def test_output_template_keeps_title_and_id() -> None:
    tmpl = output_template()
    assert tmpl == OUTPUT_TEMPLATE
    assert "%(title)" in tmpl
    assert "%(id)s" in tmpl
    assert "%(ext)s" in tmpl
