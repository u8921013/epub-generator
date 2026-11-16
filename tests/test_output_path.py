import zipfile

import pytest

from epubgen.cli import main
from tests.helpers import Epub, make_image


@pytest.fixture
def comic(tmp_path):
    folder = tmp_path / "comics" / "my-comic"
    folder.mkdir(parents=True)
    make_image(folder / "1.jpg")
    make_image(folder / "2.jpg")
    return folder


def run(*args):
    return main([str(a) for a in args])


def snapshot(folder):
    return sorted((p.relative_to(folder).as_posix(), p.read_bytes())
                  for p in folder.rglob("*") if p.is_file())


def test_output_option_writes_to_the_given_path_and_reports_it(comic, tmp_path, capsys):
    target = tmp_path / "sync" / "renamed.epub"
    target.parent.mkdir()

    code = run(comic, "-o", target)

    out = capsys.readouterr().out
    assert code == 0
    assert target.is_file()
    assert str(target) in out
    assert not (comic.parent / "my-comic.epub").exists()
    assert len(Epub(target).page_paths()) == 2


def test_long_form_output_option_is_accepted(comic, tmp_path):
    target = tmp_path / "long.epub"
    assert run(comic, "--output", target) == 0
    assert target.is_file()


def test_existing_default_output_is_refused_and_left_untouched(comic, capsys):
    existing = comic.parent / "my-comic.epub"
    existing.write_bytes(b"precious")

    code = run(comic)

    captured = capsys.readouterr()
    assert code != 0
    assert captured.err.strip() != ""
    assert str(existing) in captured.err
    assert captured.out == ""
    assert existing.read_bytes() == b"precious"


def test_existing_output_given_with_o_is_refused_and_left_untouched(comic, tmp_path, capsys):
    existing = tmp_path / "out.epub"
    existing.write_bytes(b"precious")

    code = run(comic, "-o", existing)

    assert code != 0
    assert capsys.readouterr().err.strip() != ""
    assert existing.read_bytes() == b"precious"


def test_force_overwrites_an_existing_output(comic, tmp_path, capsys):
    existing = tmp_path / "out.epub"
    existing.write_bytes(b"old")

    code = run(comic, "-o", existing, "--force")

    assert code == 0
    assert str(existing) in capsys.readouterr().out
    assert zipfile.is_zipfile(existing)
    assert len(Epub(existing).page_paths()) == 2


def test_force_overwrites_the_default_output_too(comic):
    existing = comic.parent / "my-comic.epub"
    existing.write_bytes(b"old")

    assert run(comic, "--force") == 0
    assert zipfile.is_zipfile(existing)


def test_force_without_an_existing_file_still_works(comic, tmp_path):
    target = tmp_path / "fresh.epub"
    assert run(comic, "-o", target, "--force") == 0
    assert target.is_file()


def test_failure_leaves_no_output_and_no_temp_files(comic, tmp_path, capsys):
    (comic / "3.jpg").write_bytes(b"not an image")
    target_dir = tmp_path / "dest"
    target_dir.mkdir()

    code = run(comic, "-o", target_dir / "out.epub")

    assert code != 0
    assert capsys.readouterr().err.strip() != ""
    assert list(target_dir.iterdir()) == []
    assert not (comic.parent / "my-comic.epub").exists()


def test_failure_while_writing_leaves_no_output_and_keeps_existing_file(
        comic, tmp_path, monkeypatch, capsys):
    existing = tmp_path / "dest" / "out.epub"
    existing.parent.mkdir()
    existing.write_bytes(b"precious")

    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", boom)

    code = run(comic, "-o", existing, "--force")

    assert code != 0
    assert capsys.readouterr().err.strip() != ""
    assert existing.read_bytes() == b"precious"
    assert [p.name for p in existing.parent.iterdir()] == ["out.epub"]


def test_failure_while_writing_leaves_no_new_file_behind(comic, tmp_path, monkeypatch):
    target_dir = tmp_path / "dest"
    target_dir.mkdir()

    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", boom)

    assert run(comic, "-o", target_dir / "out.epub") != 0
    assert list(target_dir.iterdir()) == []


def test_output_directory_that_does_not_exist_is_a_clean_error(comic, tmp_path, capsys):
    code = run(comic, "-o", tmp_path / "missing" / "out.epub")

    assert code != 0
    assert capsys.readouterr().err.strip() != ""
    assert not (tmp_path / "missing").exists()


def test_output_path_that_is_a_directory_is_a_clean_error(comic, tmp_path, capsys):
    code = run(comic, "-o", tmp_path)

    assert code != 0
    assert capsys.readouterr().err.strip() != ""


def test_input_folder_is_unchanged_on_success_and_on_failure(comic, tmp_path):
    before = snapshot(comic)

    run(comic)
    assert snapshot(comic) == before

    run(comic)  # 已存在，被拒絕
    assert snapshot(comic) == before

    (comic / "3.jpg").write_bytes(b"not an image")
    before = snapshot(comic)
    run(comic, "-o", tmp_path / "other.epub")
    assert snapshot(comic) == before


def test_help_lists_output_and_force(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "-o" in out
    assert "--force" in out


def test_output_file_has_the_permissions_of_a_normally_created_file(comic, tmp_path):
    import os
    import stat

    umask = os.umask(0)
    os.umask(umask)
    target = tmp_path / "perm.epub"

    run(comic, "-o", target)

    assert stat.S_IMODE(target.stat().st_mode) == 0o666 & ~umask
