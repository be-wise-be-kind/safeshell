"""Tests for safeshell.shims.manager module."""

import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from safeshell.rules.schema import Rule, RuleAction


class TestGetShimDir:
    """Tests for get_shim_dir()."""

    def test_returns_shim_dir_path(self) -> None:
        """Test that get_shim_dir returns the SHIM_DIR constant."""
        from safeshell.shims.manager import SHIM_DIR, get_shim_dir

        assert get_shim_dir() == SHIM_DIR

    def test_shim_dir_is_under_safeshell(self) -> None:
        """Test that SHIM_DIR is under ~/.safeshell/."""
        from safeshell.shims.manager import SHIM_DIR

        assert SHIM_DIR.name == "shims"
        assert SHIM_DIR.parent.name == ".safeshell"


class TestGetCommandsFromRules:
    """Tests for get_commands_from_rules()."""

    def test_returns_empty_set_when_no_rules(self) -> None:
        """Test returns empty set when no rules exist."""
        from safeshell.shims.manager import get_commands_from_rules

        with patch("safeshell.shims.manager.load_rules", return_value=[]):
            result = get_commands_from_rules("/some/dir")
            assert result == set()

    def test_extracts_commands_from_rules(self) -> None:
        """Test that commands are extracted from rules."""
        from safeshell.shims.manager import get_commands_from_rules

        mock_rules = [
            Rule(name="r1", commands=["git", "curl"], action=RuleAction.ALLOW, message="Allow"),
            Rule(name="r2", commands=["wget", "git"], action=RuleAction.DENY, message="Deny"),
        ]
        with patch("safeshell.shims.manager.load_rules", return_value=mock_rules):
            result = get_commands_from_rules("/some/dir")
            assert result == {"git", "curl", "wget"}

    def test_filters_out_builtin_commands(self) -> None:
        """Test that shell builtins are filtered out."""
        from safeshell.shims.manager import BUILTIN_COMMANDS, get_commands_from_rules

        mock_rules = [
            Rule(name="r1", commands=["git", "cd", "source", "eval"], action=RuleAction.ALLOW, message="Allow"),
        ]
        with patch("safeshell.shims.manager.load_rules", return_value=mock_rules):
            result = get_commands_from_rules("/some/dir")
            assert result == {"git"}
            # Verify builtins were filtered
            for builtin in BUILTIN_COMMANDS:
                assert builtin not in result

    def test_loads_global_rules_when_no_working_dir(self) -> None:
        """Test that global rules are loaded when working_dir is None."""
        from safeshell.shims.manager import get_commands_from_rules

        mock_rules = [Rule(name="r1", commands=["git"], action=RuleAction.ALLOW, message="Allow")]

        with (
            patch("safeshell.shims.manager.GLOBAL_RULES_PATH") as mock_path,
            patch("safeshell.rules.loader._load_rule_file", return_value=mock_rules) as mock_load,
        ):
            mock_path.exists.return_value = True
            result = get_commands_from_rules(None)
            assert result == {"git"}
            mock_load.assert_called_once_with(mock_path)

    def test_returns_empty_when_no_global_rules_exist(self) -> None:
        """Test returns empty set when global rules file doesn't exist."""
        from safeshell.shims.manager import get_commands_from_rules

        with patch("safeshell.shims.manager.GLOBAL_RULES_PATH") as mock_path:
            mock_path.exists.return_value = False
            result = get_commands_from_rules(None)
            assert result == set()


class TestGetSourceShimPath:
    """Tests for get_source_shim_path()."""

    def test_returns_path_to_shim_script(self) -> None:
        """Test that it returns path to safeshell-shim in package."""
        from safeshell.shims.manager import SHIM_SCRIPT_NAME, get_source_shim_path

        path = get_source_shim_path()
        assert path.name == SHIM_SCRIPT_NAME
        assert "shims" in str(path)


class TestEnsureShimDirectory:
    """Tests for ensure_shim_directory()."""

    def test_creates_directory_if_not_exists(self) -> None:
        """Test that directory is created if it doesn't exist."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_shims"
            with patch.object(manager, "SHIM_DIR", test_dir):
                manager.ensure_shim_directory()
                assert test_dir.exists()
                assert test_dir.is_dir()

    def test_no_error_if_directory_exists(self) -> None:
        """Test that no error if directory already exists."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_shims"
            test_dir.mkdir()
            with patch.object(manager, "SHIM_DIR", test_dir):
                # Should not raise
                manager.ensure_shim_directory()
                assert test_dir.exists()


class TestInstallShimScript:
    """Tests for install_shim_script()."""

    def test_copies_shim_script_to_directory(self) -> None:
        """Test that shim script is copied to shims directory."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_shims"
            # Create a fake source shim script
            source_shim = Path(tmpdir) / "source_shim"
            source_shim.write_text("#!/bin/bash\necho test")

            with (
                patch.object(manager, "SHIM_DIR", test_dir),
                patch.object(manager, "get_source_shim_path", return_value=source_shim),
            ):
                result = manager.install_shim_script()
                assert result.exists()
                assert result.parent == test_dir

    def test_makes_script_executable(self) -> None:
        """Test that installed script is executable."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "test_shims"
            source_shim = Path(tmpdir) / "source_shim"
            source_shim.write_text("#!/bin/bash\necho test")

            with (
                patch.object(manager, "SHIM_DIR", test_dir),
                patch.object(manager, "get_source_shim_path", return_value=source_shim),
            ):
                result = manager.install_shim_script()
                mode = result.stat().st_mode
                assert mode & stat.S_IXUSR  # User execute
                assert mode & stat.S_IXGRP  # Group execute
                assert mode & stat.S_IXOTH  # Other execute

    def test_raises_if_source_not_found(self) -> None:
        """Test raises FileNotFoundError if source shim not found."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"
            with patch.object(manager, "get_source_shim_path", return_value=nonexistent):
                with pytest.raises(FileNotFoundError):
                    manager.install_shim_script()


class TestCreateShim:
    """Tests for create_shim()."""

    def test_creates_symlink_to_shim_script(self) -> None:
        """Test that a symlink is created to the shim script."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.create_shim("git")
                assert result.is_symlink()
                assert result.name == "git"
                assert str(result.readlink()) == manager.SHIM_SCRIPT_NAME

    def test_removes_existing_symlink_before_creating(self) -> None:
        """Test that existing symlink is removed before creating new one."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            # Create existing symlink
            existing = test_dir / "git"
            existing.symlink_to("old_target")

            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.create_shim("git")
                assert result.is_symlink()
                assert str(result.readlink()) == manager.SHIM_SCRIPT_NAME

    def test_skips_if_regular_file_exists(self) -> None:
        """Test that regular files are not overwritten."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            # Create a regular file
            regular_file = test_dir / "git"
            regular_file.write_text("I am a real file")

            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.create_shim("git")
                # File should still be a regular file, not symlink
                assert not result.is_symlink()
                assert regular_file.read_text() == "I am a real file"


class TestRemoveShim:
    """Tests for remove_shim()."""

    def test_removes_existing_symlink(self) -> None:
        """Test that existing symlink is removed."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            shim = test_dir / "git"
            shim.symlink_to("target")

            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.remove_shim("git")
                assert result is True
                assert not shim.exists()

    def test_returns_false_if_not_exists(self) -> None:
        """Test returns False if shim doesn't exist."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.remove_shim("nonexistent")
                assert result is False

    def test_returns_false_if_not_symlink(self) -> None:
        """Test returns False if path is not a symlink."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            regular_file = test_dir / "git"
            regular_file.write_text("regular file")

            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.remove_shim("git")
                assert result is False
                # File should still exist
                assert regular_file.exists()


class TestGetExistingShims:
    """Tests for get_existing_shims()."""

    def test_returns_empty_if_dir_not_exists(self) -> None:
        """Test returns empty set if shims directory doesn't exist."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"
            with patch.object(manager, "SHIM_DIR", nonexistent):
                result = manager.get_existing_shims()
                assert result == set()

    def test_returns_symlinks_only(self) -> None:
        """Test returns only symlink names, not regular files."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            # Create symlinks
            (test_dir / "git").symlink_to("target")
            (test_dir / "curl").symlink_to("target")
            # Create regular file
            (test_dir / "regular").write_text("file")

            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.get_existing_shims()
                assert result == {"git", "curl"}
                assert "regular" not in result

    def test_excludes_shim_script_itself(self) -> None:
        """Test excludes the safeshell-shim script from results."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            (test_dir / "git").symlink_to("target")
            # Create the shim script (as file)
            (test_dir / manager.SHIM_SCRIPT_NAME).write_text("script")

            with patch.object(manager, "SHIM_DIR", test_dir):
                result = manager.get_existing_shims()
                assert result == {"git"}
                assert manager.SHIM_SCRIPT_NAME not in result


class TestRefreshShims:
    """Tests for refresh_shims()."""

    def test_creates_new_shims(self) -> None:
        """Test creates shims for commands in rules."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "shims"
            source_shim = Path(tmpdir) / "source_shim"
            source_shim.write_text("#!/bin/bash")

            mock_rules = [Rule(name="r1", commands=["git", "curl"], action=RuleAction.ALLOW, message="Allow")]

            with (
                patch.object(manager, "SHIM_DIR", test_dir),
                patch.object(manager, "get_source_shim_path", return_value=source_shim),
                patch("safeshell.shims.manager.load_rules", return_value=mock_rules),
            ):
                result = manager.refresh_shims("/some/dir")

                assert "git" in result["created"]
                assert "curl" in result["created"]
                assert (test_dir / "git").is_symlink()
                assert (test_dir / "curl").is_symlink()

    def test_removes_stale_shims(self) -> None:
        """Test removes shims not in current rules."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "shims"
            test_dir.mkdir()
            source_shim = Path(tmpdir) / "source_shim"
            source_shim.write_text("#!/bin/bash")

            # Create existing shim
            (test_dir / "oldcmd").symlink_to("target")

            # Rules don't include oldcmd
            mock_rules = [Rule(name="r1", commands=["git"], action=RuleAction.ALLOW, message="Allow")]

            with (
                patch.object(manager, "SHIM_DIR", test_dir),
                patch.object(manager, "get_source_shim_path", return_value=source_shim),
                patch("safeshell.shims.manager.load_rules", return_value=mock_rules),
            ):
                result = manager.refresh_shims("/some/dir")

                assert "oldcmd" in result["removed"]
                assert not (test_dir / "oldcmd").exists()

    def test_tracks_unchanged_shims(self) -> None:
        """Test tracks shims that already exist and are in rules."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / "shims"
            test_dir.mkdir()
            source_shim = Path(tmpdir) / "source_shim"
            source_shim.write_text("#!/bin/bash")

            # Create existing shim that's in rules
            (test_dir / "git").symlink_to("target")

            mock_rules = [Rule(name="r1", commands=["git"], action=RuleAction.ALLOW, message="Allow")]

            with (
                patch.object(manager, "SHIM_DIR", test_dir),
                patch.object(manager, "get_source_shim_path", return_value=source_shim),
                patch("safeshell.shims.manager.load_rules", return_value=mock_rules),
            ):
                result = manager.refresh_shims("/some/dir")

                assert "git" in result["unchanged"]
                assert result["created"] == []
                assert result["removed"] == []


class TestGetInitScriptPath:
    """Tests for get_init_script_path()."""

    def test_returns_path_to_init_bash(self) -> None:
        """Test returns path to init.bash in package."""
        from safeshell.shims.manager import get_init_script_path

        path = get_init_script_path()
        assert path.name == "init.bash"
        assert "shims" in str(path)


class TestInstallInitScript:
    """Tests for install_init_script()."""

    def test_copies_init_script_to_safeshell_dir(self) -> None:
        """Test that init.bash is copied to ~/.safeshell/."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            test_safeshell_dir = Path(tmpdir)
            source_init = Path(tmpdir) / "source_init.bash"
            source_init.write_text("source script content")

            with (
                patch("safeshell.shims.manager.SAFESHELL_DIR", test_safeshell_dir),
                patch.object(manager, "get_init_script_path", return_value=source_init),
            ):
                result = manager.install_init_script()
                assert result.exists()
                assert result.name == "init.bash"
                assert result.read_text() == "source script content"

    def test_raises_if_source_not_found(self) -> None:
        """Test raises FileNotFoundError if source init script not found."""
        from safeshell.shims import manager

        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent"
            with patch.object(manager, "get_init_script_path", return_value=nonexistent):
                with pytest.raises(FileNotFoundError):
                    manager.install_init_script()


class TestGetShellInitInstructions:
    """Tests for get_shell_init_instructions()."""

    def test_returns_instructions_string(self) -> None:
        """Test returns non-empty instructions string."""
        from safeshell.shims.manager import get_shell_init_instructions

        result = get_shell_init_instructions()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_shell_config_references(self) -> None:
        """Test instructions mention shell config files."""
        from safeshell.shims.manager import get_shell_init_instructions

        result = get_shell_init_instructions()
        assert ".bashrc" in result or "bashrc" in result.lower()
        assert ".zshrc" in result or "zshrc" in result.lower()

    def test_contains_source_command(self) -> None:
        """Test instructions include source command."""
        from safeshell.shims.manager import get_shell_init_instructions

        result = get_shell_init_instructions()
        assert "source" in result

    def test_contains_init_bash_path(self) -> None:
        """Test instructions include path to init.bash."""
        from safeshell.shims.manager import get_shell_init_instructions

        result = get_shell_init_instructions()
        assert "init.bash" in result


class TestBuiltinCommands:
    """Tests for BUILTIN_COMMANDS constant."""

    def test_contains_common_shell_builtins(self) -> None:
        """Test that common shell builtins are in the set."""
        from safeshell.shims.manager import BUILTIN_COMMANDS

        assert "cd" in BUILTIN_COMMANDS
        assert "source" in BUILTIN_COMMANDS
        assert "eval" in BUILTIN_COMMANDS
        assert "export" in BUILTIN_COMMANDS

    def test_is_frozen_set(self) -> None:
        """Test that BUILTIN_COMMANDS is a frozenset (immutable)."""
        from safeshell.shims.manager import BUILTIN_COMMANDS

        assert isinstance(BUILTIN_COMMANDS, frozenset)
