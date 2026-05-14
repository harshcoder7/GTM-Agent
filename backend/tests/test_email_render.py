from services.email_render import render_email_html, brochure_html, _apply_inline_markdown


def test_inline_markdown_pink_bold():
    out = _apply_inline_markdown("Try ***QpiAI Pro*** today")
    assert "rgb(204,43,156)" in out
    assert "QpiAI Pro" in out


def test_brochure_both():
    out = brochure_html("Both")
    assert "QpiAI Pro Brochure" in out
    assert "QpiAI Agent Hive Brochure" in out


def test_render_email_full():
    draft = {
        "subject": "Hello",
        "greeting": "Hey Sam,",
        "introduction": "Saw your work on **vision models**.",
        "pain_point": "Manual annotation is slow.",
        "product_desc": "***QpiAI Pro*** automates the pipeline.",
        "bullet_points": ["🚀 **50%** faster", "💵 *Lower* costs"],
        "cta": "Open to a quick chat?",
    }
    html = render_email_html(draft, "Pro")
    assert "Hey Sam," in html
    assert "QpiAI Pro Brochure" in html
    assert "<ul" in html and "<li" in html
