from qmi_engine import robust_growth, log_rs, score, inflection_velocity

COMP = {"a":{"x":60,"y":40}, "b":{"z":100}}

def test_coverage_shrinkage():
    r = score({"x":90,"y":None,"z":90}, COMP)
    assert round(r.coverage,2) == .80
    assert round(r.raw_mcs,2) == 82.0
    assert round(r.adjusted_mcs,2) == 75.6

def test_robust_growth_negative_base_is_bounded_by_scale():
    assert robust_growth(5,-1,100) == 3

def test_relative_strength():
    assert log_rs(120,100,110,100) > 0

def test_velocity():
    v = inflection_velocity(81,70,57)
    assert v["velocity_1m"] == 11
    assert v["velocity_3m"] == 24
    assert v["acceleration"] == 3

