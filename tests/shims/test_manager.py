"""Tests for the shim manager module.

Tests shim creation, removal, and synchronization with rules.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from safeshell.rules.schema import Rule
from safeshell.shims import manager


class TestGetShimDir:
    """Tests for get_shim_dir()."""

    def test_returns_path_object(self):
        """get_shim_dir returns a Path object."""
        result = manager.get_shim_dir()
        assert isinstance(result, Path)

    def test_returns_shim_dir_constant(self):
        """get_shim_dir returns the SHIM_DIR constant."""
        result = manager.get_shim_dir()
        assert result == manager.SHIM_DIR


class TestEnsureShimDirectory:
    """Tests for ensure_shim_directory()."""

    def test_creates_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Creates the shim directory if it doesn't exist."""
        shim_dir = tmp_path / "shims"
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        assert not shim_dir.exists()
        manager.ensure_shim_directory()
        assert shim_dir.exists()
        assert shim_dir.is_dir()

    def test_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Calling multiple times is safe."""
        shim_dir = tmp_path / "shims"
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        manager.ensure_shim_directory()
        manager.ensure_shim_directory()  # Should not raise
        assert shim_dir.exists()


class TestCreateShim:
    """Tests for create_shim()."""

    def test_creates_symlink(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Creates a symlink for the command."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        result = manager.create_shim("git")

        assert result == shim_dir / "git"
        assert result.is_symlink()
        assert result.readlink() == Path(manager.SHIM_SCRIPT_NAME)

    def test_overwrites_existing_symlink(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Replaces an existing symlink."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create an old symlink pointing somewhere else
        old_link = shim_dir / "git"
        old_link.symlink_to("old-target")
        assert old_link.readlink() == Path("old-target")

        # create_shim should replace it
        manager.create_shim("git")
        assert old_link.readlink() == Path(manager.SHIM_SCRIPT_NAME)

    def test_skips_real_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Does not overwrite a real file (not a symlink)."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a real file
        real_file = shim_dir / "git"
        real_file.write_text("real content")

        result = manager.create_shim("git")

        # Should return the path but not modify it
        assert result == real_file
        assert not real_file.is_symlink()
        assert real_file.read_text() == "real content"


class TestRemoveShim:
    """Tests for remove_shim()."""

    def test_removes_symlink(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Removes an existing symlink."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a symlink (broken symlinks still need to be removable)
        link = shim_dir / "git"
        link.symlink_to("target")
        assert link.is_symlink()  # Use is_symlink() since target doesn't exist

        result = manager.remove_shim("git")

        assert result is True
        assert not link.is_symlink()

    def test_returns_false_if_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Returns False if the shim doesn't exist."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        result = manager.remove_shim("nonexistent")

        assert result is False

    def test_skips_real_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Does not remove a real file (not a symlink)."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a real file
        real_file = shim_dir / "git"
        real_file.write_text("real content")

        result = manager.remove_shim("git")

        assert result is False
        assert real_file.exists()


class TestGetExistingShims:
    """Tests for get_existing_shims()."""

    def test_returns_empty_for_new_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Returns empty set for a new/empty directory."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        result = manager.get_existing_shims()

        assert result == set()

    def test_returns_empty_if_dir_not_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Returns empty set if shim directory doesn't exist."""
        shim_dir = tmp_path / "nonexistent"
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        result = manager.get_existing_shims()

        assert result == set()

    def test_lists_symlinks_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Only returns symlinks, not regular files."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create some symlinks
        (shim_dir / "git").symlink_to("target")
        (shim_dir / "rm").symlink_to("target")
        # Create a regular file (should be ignored)
        (shim_dir / "regular.txt").write_text("content")
        # Create the shim script (should be ignored)
        (shim_dir / manager.SHIM_SCRIPT_NAME).write_text("script")

        result = manager.get_existing_shims()

        assert result == {"git", "rm"}


class TestGetCommandsFromRules:
    """Tests for get_commands_from_rules()."""

    def test_extracts_commands(self, monkeypatch: pytest.MonkeyPatch):
        """Extracts unique commands from rules."""
        mock_rules = [
            Rule(
                name="test1",
                commands=["git", "rm"],
                conditions=[{"command_contains": "test"}],
                action="allow",
                message="Test rule 1",
            ),
            Rule(
                name="test2",
                commands=["docker", "git"],  # git is duplicate
                conditions=[{"command_contains": "test"}],
                action="allow",
                message="Test rule 2",
            ),
        ]

        with patch.object(manager, "load_rules", return_value=mock_rules):
            result = manager.get_commands_from_rules("/some/path")

        assert result == {"git", "rm", "docker"}

    def test_skips_builtins(self, monkeypatch: pytest.MonkeyPatch):
        """Does not include shell builtins (handled by init.bash)."""
        mock_rules = [
            Rule(
                name="test1",
                commands=["git", "cd", "source", "eval"],  # cd, source, eval are builtins
                conditions=[{"command_contains": "test"}],
                action="allow",
                message="Test rule with builtins",
            ),
        ]

        with patch.object(manager, "load_rules", return_value=mock_rules):
            result = manager.get_commands_from_rules("/some/path")

        assert result == {"git"}
        assert "cd" not in result
        assert "source" not in result
        assert "eval" not in result


class TestRefreshShims:
    """Tests for refresh_shims()."""

    def test_creates_new_shims(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Creates shims for commands that don't have them yet."""
        shim_dir = tmp_path / "shims"
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a fake shim script source
        source_shim = tmp_path / "source_shim"
        source_shim.write_text("#!/bin/bash\necho shim")
        monkeypatch.setattr(manager, "get_source_shim_path", lambda: source_shim)

        mock_rules = [
            Rule(
                name="test1",
                commands=["git", "rm"],
                conditions=[{"command_contains": "test"}],
                action="allow",
                message="Test rule",
            ),
        ]

        with patch.object(manager, "load_rules", return_value=mock_rules):
            result = manager.refresh_shims("/some/path")

        assert "git" in result["created"]
        assert "rm" in result["created"]
        assert (shim_dir / "git").is_symlink()
        assert (shim_dir / "rm").is_symlink()

    def test_removes_stale_shims(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Removes shims for commands no longer in rules."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a fake shim script source
        source_shim = tmp_path / "source_shim"
        source_shim.write_text("#!/bin/bash\necho shim")
        monkeypatch.setattr(manager, "get_source_shim_path", lambda: source_shim)

        # Create existing shims
        (shim_dir / "git").symlink_to("target")
        (shim_dir / "old_command").symlink_to("target")

        # Rules only include git, not old_command
        mock_rules = [
            Rule(
                name="test1",
                commands=["git"],
                conditions=[{"command_contains": "test"}],
                action="allow",
                message="Test rule",
            ),
        ]

        with patch.object(manager, "load_rules", return_value=mock_rules):
            result = manager.refresh_shims("/some/path")

        assert "old_command" in result["removed"]
        assert not (shim_dir / "old_command").exists()
        assert "git" in result["unchanged"]

    def test_tracks_unchanged(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Reports shims that already exist and are still needed."""
        shim_dir = tmp_path / "shims"
        shim_dir.mkdir()
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a fake shim script source
        source_shim = tmp_path / "source_shim"
        source_shim.write_text("#!/bin/bash\necho shim")
        monkeypatch.setattr(manager, "get_source_shim_path", lambda: source_shim)

        # Create existing shim
        (shim_dir / "git").symlink_to("target")

        mock_rules = [
            Rule(
                name="test1",
                commands=["git"],
                conditions=[{"command_contains": "test"}],
                action="allow",
                message="Test rule",
            ),
        ]

        with patch.object(manager, "load_rules", return_value=mock_rules):
            result = manager.refresh_shims("/some/path")

        assert "git" in result["unchanged"]
        assert result["created"] == []
        assert result["removed"] == []


class TestInstallShimScript:
    """Tests for install_shim_script()."""

    def test_copies_script_and_makes_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Copies the shim script and makes it executable."""
        shim_dir = tmp_path / "shims"
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        # Create a fake source shim script
        source_shim = tmp_path / "source_shim"
        source_shim.write_text("#!/bin/bash\necho shim")
        monkeypatch.setattr(manager, "get_source_shim_path", lambda: source_shim)

        result = manager.install_shim_script()

        assert result == shim_dir / manager.SHIM_SCRIPT_NAME
        assert result.exists()
        assert result.read_text() == "#!/bin/bash\necho shim"
        # Check executable bit
        import stat

        assert result.stat().st_mode & stat.S_IXUSR

    def test_raises_if_source_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Raises FileNotFoundError if source shim script doesn't exist."""
        shim_dir = tmp_path / "shims"
        monkeypatch.setattr(manager, "SHIM_DIR", shim_dir)

        nonexistent = tmp_path / "nonexistent"
        monkeypatch.setattr(manager, "get_source_shim_path", lambda: nonexistent)

        with pytest.raises(FileNotFoundError):
            manager.install_shim_script()


class TestGetSourceShimPath:
    """Tests for get_source_shim_path()."""

    def test_returns_path_in_package(self):
        """Returns the path to the shim script in the package."""
        result = manager.get_source_shim_path()
        assert isinstance(result, Path)
        assert result.name == manager.SHIM_SCRIPT_NAME


class TestGetInitScriptPath:
    """Tests for get_init_script_path()."""

    def test_returns_path_to_init_bash(self):
        """Returns path to init.bash in the package."""
        result = manager.get_init_script_path()
        assert isinstance(result, Path)
        assert result.name == "init.bash"


class TestGetShellInitInstructions:
    """Tests for get_shell_init_instructions()."""

    def test_returns_string_with_source_command(self):
        """Returns instructions that include sourcing the init script."""
        result = manager.get_shell_init_instructions()
        assert isinstance(result, str)
        assert "source" in result
        assert "init.bash" in result
        assert ".bashrc" in result or "bash" in result.lower()
