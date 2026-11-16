from tools.demo import main


def test_demo_shows_ground_go_and_spraywait_stop(capsys):
    """The default inversion scenario prints GO for the ground station and STOP for SprayWait."""
    main([])
    out = capsys.readouterr().out
    assert "Ground station only: GO" in out
    assert "SprayWait: STOP" in out


def test_demo_accepts_scenario_argument(capsys):
    """A scenario name on the command line selects that scenario."""
    main(["clear_midday"])
    assert "SprayWait: GO" in capsys.readouterr().out
