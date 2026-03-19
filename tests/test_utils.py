import os
import json
import pytest
from datetime import datetime

from paintdry.utils import timestamp, sha, merge, shell, ensure_folder, ensure_json_file, JsonFile


def test_timestamp_returns_iso_format():
    ts = timestamp()
    datetime.fromisoformat(ts)


def test_timestamp_returns_string():
    assert isinstance(timestamp(), str)


def test_sha_known_hash():
    assert sha("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_sha_deterministic():
    assert sha("hello") == sha("hello")


def test_sha_different_inputs_differ():
    assert sha("a") != sha("b")


def test_sha_returns_hex_string():
    result = sha("test")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_merge_string_replaced():
    assert merge("a", "b") == "b"


def test_merge_int_replaced():
    assert merge(1, 2) == 2


def test_merge_list_concatenated_no_duplicates():
    assert merge([1, 2], [2, 3]) == [1, 2, 3]


def test_merge_list_replaced_by_non_list():
    assert merge([1, 2], "x") == "x"


def test_merge_dict_merged():
    a = {"x": 1, "y": 2}
    b = {"y": 3, "z": 4}
    assert merge(a, b) == {"x": 1, "y": 3, "z": 4}


def test_merge_dict_replaced_by_non_dict():
    assert merge({"a": 1}, "x") == "x"


def test_merge_nested_dict():
    a = {"outer": {"a": 1, "b": 2}}
    b = {"outer": {"b": 3, "c": 4}}
    assert merge(a, b) == {"outer": {"a": 1, "b": 3, "c": 4}}


def test_merge_does_not_mutate_inputs():
    a = {"x": [1, 2]}
    b = {"x": [3]}
    merge(a, b)
    assert a == {"x": [1, 2]}
    assert b == {"x": [3]}


def test_merge_list_empty():
    assert merge([], [1]) == [1]
    assert merge([1], []) == [1]


def test_merge_dict_empty():
    assert merge({}, {"a": 1}) == {"a": 1}
    assert merge({"a": 1}, {}) == {"a": 1}


def test_shell_simple_command():
    exit_code, stdout, stderr = shell("echo hello")
    assert exit_code == 0
    assert stdout.strip() == "hello"
    assert stderr == ""


def test_shell_failing_command():
    exit_code, stdout, stderr = shell("false")
    assert exit_code != 0
    assert stdout == ""
    assert stderr == ""


def test_shell_check_raises_on_failure():
    with pytest.raises(ValueError):
        shell("false", check=True)


def test_shell_check_passes_on_success():
    exit_code, stdout, stderr = shell("true", check=True)
    assert exit_code == 0
    assert stdout == ""
    assert stderr == ""


def test_shell_accepts_list():
    exit_code, stdout, stderr = shell(["echo", "hello"])
    assert exit_code == 0
    assert stdout == "hello\n"
    assert stderr == ""


def test_shell_stderr_captured():
    exit_code, stdout, stderr = shell("echo err >&2")
    assert exit_code == 0
    assert stdout == ""
    assert stderr == "err\n"


def test_ensure_folder_creates_folder(tmp_path):
    path = str(tmp_path / "new_dir")
    result = ensure_folder(path)
    assert os.path.isdir(path)
    assert result == path


def test_ensure_folder_existing_folder(tmp_path):
    path = str(tmp_path / "existing")
    os.mkdir(path)
    result = ensure_folder(path)
    assert result == path


def test_ensure_folder_exits_if_file_exists(tmp_path):
    path = str(tmp_path / "afile")
    with open(path, "w") as f:
        f.write("x")
    with pytest.raises(SystemExit):
        ensure_folder(path)


def test_ensure_json_file_creates_with_default(tmp_path):
    path = str(tmp_path / "data.json")
    ensure_json_file(path, {"key": "value"})
    with open(path, "r") as f:
        data = json.loads(f.read())
    assert data == {"key": "value"}


def test_ensure_json_file_existing_unchanged(tmp_path):
    path = str(tmp_path / "data.json")
    with open(path, "w") as f:
        f.write(json.dumps({"existing": True}, indent=2) + "\n")
    ensure_json_file(path, {"default": True})
    with open(path, "r") as f:
        data = json.loads(f.read())
    assert data == {"existing": True}


def test_ensure_json_file_rejects_non_json_extension(tmp_path):
    path = str(tmp_path / "data.txt")
    with pytest.raises(SystemExit):
        ensure_json_file(path, {})


def test_ensure_json_file_exits_if_directory(tmp_path):
    path = str(tmp_path / "dir.json")
    os.mkdir(path)
    with pytest.raises(SystemExit):
        ensure_json_file(path, {})


def test_json_file_create_and_read(tmp_path):
    path = str(tmp_path / "test.json")
    jf = JsonFile(path, {"a": 1})
    assert jf["a"] == 1


def test_json_file_setitem_saves(tmp_path):
    path = str(tmp_path / "test.json")
    jf = JsonFile(path, {"a": 1})
    jf["a"] = 2
    with open(path, "r") as f:
        data = json.loads(f.read())
    assert data["a"] == 2


def test_json_file_contains(tmp_path):
    path = str(tmp_path / "test.json")
    jf = JsonFile(path, {"x": 1})
    assert "x" in jf
    assert "y" not in jf


def test_json_file_get_with_default(tmp_path):
    path = str(tmp_path / "test.json")
    jf = JsonFile(path, {"x": 1})
    assert jf.get("x", 99) == 1
    assert jf.get("missing", 99) == 99


def test_json_file_load_reloads_from_disk(tmp_path):
    path = str(tmp_path / "test.json")
    jf = JsonFile(path, {"a": 1})
    with open(path, "w") as f:
        f.write(json.dumps({"a": 42}, indent=2) + "\n")
    jf.load()
    assert jf["a"] == 42


def test_json_file_save_to_different_path(tmp_path):
    path = str(tmp_path / "test.json")
    other = str(tmp_path / "other.json")
    jf = JsonFile(path, {"a": 1})
    jf.save(other)
    with open(other, "r") as f:
        data = json.loads(f.read())
    assert data == {"a": 1}


def test_json_file_default_not_mutated(tmp_path):
    default = {"items": [1]}
    path1 = str(tmp_path / "a.json")
    path2 = str(tmp_path / "b.json")
    jf1 = JsonFile(path1, default)
    jf1["items"] = [1, 2, 3]
    jf2 = JsonFile(path2, default)
    assert jf2["items"] == [1]
