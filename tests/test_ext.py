import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from apu import ext  # noqa: E402


def test_front_app():
    line = "  mCurrentFocus=Window{9a3 u0 jp.pokemon.pokemonunite/com.unity3d.player.UnityPlayerActivity}"
    assert ext.front_app(line) == "jp.pokemon.pokemonunite"
    assert ext.is_unite("jp.pokemon.pokemonunite")
    assert not ext.is_unite("com.supersolid.honestfood")
    assert ext.front_app("") == ""


def test_run_job_logs_only(tmp_path):
    seen = []
    r = ext.run_job({"log": seen.append, "stop": None, "logs_dir": str(tmp_path),
                     "shell": lambda c: "mCurrentFocus=Window{1 u0 com.supersolid.honestfood/x.Main}"})
    assert r == "logged" and "not in front" in seen[0]
    assert (tmp_path / "unite_log.txt").read_text().count("job turn") == 1
