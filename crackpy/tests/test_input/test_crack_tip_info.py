from crackpy.input.crack_tip_info import CrackTipInfo


def test_crack_tip_info_keeps_id_separate_from_compatibility_side():
    crack_tip = CrackTipInfo(
        crack_tip_x=1.0,
        crack_tip_y=2.0,
        crack_tip_angle=3.0,
        left_or_right="right",
        crack_tip_id="crack_tip:specimen-a:notch-2",
    )

    assert crack_tip.crack_tip_id == "crack_tip:specimen-a:notch-2"
    assert crack_tip.left_or_right == "right"

    crack_tip.set_manually(
        crack_tip_x=4.0,
        crack_tip_y=5.0,
        crack_tip_angle=6.0,
        left_or_right="left",
        crack_tip_id="crack_tip:specimen-a:notch-1",
    )

    assert crack_tip.crack_tip_id == "crack_tip:specimen-a:notch-1"
    assert crack_tip.left_or_right == "left"
