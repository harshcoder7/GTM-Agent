from services.safety import (check_placeholder_leak, check_spammy_subject,
                              check_icp_fit, check_brochure_attached)


def test_placeholder_leak_caught():
    d = {"introduction": "Hi {{first_name}}", "subject": "x", "greeting": "", "pain_point": "",
         "product_desc": "", "bullet_points": [], "cta": ""}
    r = check_placeholder_leak(d)
    assert r["passed"] is False
    assert "first_name" in r["explanation"]


def test_placeholder_clean():
    d = {"introduction": "Hi Sam", "subject": "x", "greeting": "", "pain_point": "",
         "product_desc": "", "bullet_points": [], "cta": ""}
    assert check_placeholder_leak(d)["passed"] is True


def test_spammy_subject():
    assert check_spammy_subject({"subject": "ACT NOW free!!!"})["passed"] is False
    assert check_spammy_subject({"subject": "Faster ML deploys at Acme"})["passed"] is True


def test_icp_fit_thresholds():
    assert check_icp_fit({"icp_score": 8})["passed"] is True
    assert check_icp_fit({"icp_score": 4})["passed"] is False
    assert check_icp_fit(None)["passed"] is False


def test_brochure_required():
    assert check_brochure_attached("Pro")["passed"] is True
    assert check_brochure_attached(None)["passed"] is False
    assert check_brochure_attached("garbage")["passed"] is False
