import subprocess


def test_collect_smoke_test():
    cmd = ["python", "-m", "swebench.collect.print_pulls", "--help"]
    result = subprocess.run(cmd, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0


def test_collect_one(tmp_path):
    cmd = ["python", "-m", "swebench.collect.print_pulls", "pvlib/pvlib-python", str(tmp_path/ "out.txt"), "--max-pulls", "1"]
    print(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    assert result.returncode == 0