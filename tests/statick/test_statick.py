"""Unit tests of statick.py."""

import contextlib
import os
import shutil
import subprocess
import sys

import mock
import pytest

from statick_tool.args import Args
from statick_tool.plugins.tool.clang_tidy_tool_plugin import ClangTidyToolPlugin
from statick_tool.statick import Statick


# From https://stackoverflow.com/questions/2059482/python-temporarily-modify-the-current-processs-environment
@contextlib.contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.
    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


@pytest.fixture
def init_statick():
    """Fixture to initialize a Statick instance."""
    args = Args("Statick tool")

    return Statick(args.get_user_paths(["--user-paths", os.path.dirname(__file__)]))


def test_gather_args(init_statick):
    """
    Test setting and getting arguments.

    Expected result: Arguments are set properly
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--output-directory",
        os.path.dirname(__file__),
        "--path",
        os.path.dirname(__file__),
    ]
    parsed_args = args.get_args(sys.argv)
    assert "path" in parsed_args
    assert "output_directory" in parsed_args


# The Profile module has more in-depth test cases, this test module is just
# concerned with the possible returns from the constructor.
def test_get_level(init_statick):
    """
    Test searching for a level which has a corresponding file.

    Expected result: Some level is returned
    """
    args = Args("Statick tool")
    args.parser.add_argument(
        "--profile", dest="profile", type=str, default="profile-test.yaml"
    )
    level = init_statick.get_level("some_package", args.get_args([]))
    assert level == "default_value"


def test_get_level_non_default(init_statick):
    """
    Test searching for a level when a package has a custom level.

    Expected result: Some level is returned
    """
    args = Args("Statick tool")
    args.parser.add_argument(
        "--profile", dest="profile", type=str, default="profile-test.yaml"
    )
    level = init_statick.get_level("package", args.get_args([]))
    assert level == "package_specific"


def test_get_level_nonexistent_file(init_statick):
    """
    Test searching for a level which doesn't have a corresponding file.

    Expected result: None is returned
    """
    args = Args("Statick tool")
    args.parser.add_argument(
        "--profile", dest="profile", type=str, default="nonexistent.yaml"
    )
    level = init_statick.get_level("some_package", args.get_args([]))
    assert level is None


@mock.patch("statick_tool.statick.Profile")
def test_get_level_ioerror(mocked_profile_constructor, init_statick):
    """
    Test the behavior when Profile throws an OSError.

    Expected result: None is returned
    """
    mocked_profile_constructor.side_effect = OSError("error")
    args = Args("Statick tool")
    args.parser.add_argument(
        "--profile", dest="profile", type=str, default="profile-test.yaml"
    )
    level = init_statick.get_level("some_package", args.get_args([]))
    assert level is None


def test_custom_exceptions_file(init_statick):
    """
    Test finding ignored packages specified in custom file.

    Expected result: Some ignored package is returned
    """
    args = Args("Statick tool")
    args.parser.add_argument(
        "--exceptions", dest="exceptions", type=str, default="exceptions-test.yaml"
    )
    init_statick.get_exceptions(args.get_args([]))
    ignore_packages = init_statick.get_ignore_packages()
    assert ignore_packages == ["test_package"]


def test_exceptions_no_file(init_statick):
    """
    Test finding ignored packages without specifying an exceptions file.

    Expected result: ignored packages list is empty
    """
    ignore_packages = init_statick.get_ignore_packages()
    assert not ignore_packages


def test_custom_config_file(init_statick):
    """
    Test using custom config file.

    Expected result: Some ignored package is returned
    """
    args = Args("Statick tool")
    args.parser.add_argument(
        "--config", dest="config", type=str, default="config-test.yaml"
    )
    init_statick.get_config(args.get_args([]))
    has_level = init_statick.config.has_level("default_value")
    assert has_level


@mock.patch("statick_tool.statick.Profile")
def test_get_level_valueerror(mocked_profile_constructor, init_statick):
    """Test the behavior when Profile throws a ValueError."""
    mocked_profile_constructor.side_effect = ValueError("error")
    args = Args("Statick tool")
    args.parser.add_argument(
        "--profile", dest="profile", type=str, default="profile-test.yaml"
    )
    level = init_statick.get_level("some_package", args.get_args([]))
    assert level is None


@mock.patch("statick_tool.statick.Config")
def test_get_config_valueerror(mocked_config_constructor, init_statick):
    """Test the behavior when Config throws a ValueError."""
    mocked_config_constructor.side_effect = ValueError("error")
    args = Args("Statick tool")
    args.parser.add_argument(
        "--config", dest="config", type=str, default="config-test.yaml"
    )
    init_statick.get_config(args.get_args([]))
    assert init_statick.config is None


@mock.patch("statick_tool.statick.Config")
def test_get_config_oserror(mocked_config_constructor, init_statick):
    """Test the behavior when Config throws a OSError."""
    mocked_config_constructor.side_effect = OSError("error")
    args = Args("Statick tool")
    args.parser.add_argument(
        "--config", dest="config", type=str, default="config-test.yaml"
    )
    init_statick.get_config(args.get_args([]))
    assert init_statick.config is None


@mock.patch("statick_tool.statick.Exceptions")
def test_get_exceptions_valueerror(mocked_exceptions_constructor, init_statick):
    """Test the behavior when Exceptions throws a ValueError."""
    mocked_exceptions_constructor.side_effect = ValueError("error")
    args = Args("Statick tool")
    args.parser.add_argument(
        "--exceptions", dest="exceptions", type=str, default="exceptions-test.yaml"
    )
    init_statick.get_exceptions(args.get_args([]))
    assert init_statick.exceptions is None


@mock.patch("statick_tool.statick.Exceptions")
def test_get_exceptions_oserror(mocked_exceptions_constructor, init_statick):
    """Test the behavior when Exceptions throws a OSError."""
    mocked_exceptions_constructor.side_effect = OSError("error")
    args = Args("Statick tool")
    args.parser.add_argument(
        "--exceptions", dest="exceptions", type=str, default="exceptions-test.yaml"
    )
    init_statick.get_exceptions(args.get_args([]))
    assert init_statick.exceptions is None


def test_run():
    """Test running Statick."""
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--output-directory",
        os.path.dirname(__file__),
        "--path",
        os.path.dirname(__file__),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    for tool in issues:
        assert not issues[tool]
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_missing_path(init_statick):
    """Test running Statick against a package that does not exist."""
    args = Args("Statick tool")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = ["--output-directory", os.path.dirname(__file__)]
    parsed_args = args.get_args(sys.argv)
    path = "/tmp/invalid"
    statick.get_config(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_missing_config(init_statick):
    """Test running Statick with a missing config file."""
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--output-directory",
        os.path.dirname(__file__),
        "--path",
        os.path.dirname(__file__),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_output_is_not_directory(init_statick):
    """Test running Statick against a missing directory."""
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--output-directory",
        "/tmp/not_a_directory",
        "--path",
        os.path.dirname(__file__),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_force_tool_list(init_statick):
    """Test running Statick against a missing directory."""
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = ["--path", os.path.dirname(__file__), "--force-tool-list", "bandit"]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    for tool in issues:
        assert not issues[tool]
    assert success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_package_is_ignored(init_statick):
    """
    Test that ignored package is ignored.

    Expected results: issues is empty and success is True
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.join(os.path.dirname(__file__), "test_package"),
        "--exceptions",
        os.path.join(os.path.dirname(__file__), "rsc", "exceptions-test.yaml"),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert not issues
    assert success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_invalid_discovery_plugin(init_statick):
    """
    Test that a non-existent discovery plugin results in failure.

    Expected results: issues is None and success is False
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--profile",
        os.path.join(os.path.dirname(__file__), "rsc", "profile-test.yaml"),
        "--config",
        os.path.join(os.path.dirname(__file__), "rsc", "config-test.yaml"),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_invalid_tool_plugin(init_statick):
    """
    Test that a non-existent tool plugin results in failure.

    Expected results: issues is None and success is False
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--profile",
        os.path.join(os.path.dirname(__file__), "rsc", "profile-missing-tool.yaml"),
        "--config",
        os.path.join(os.path.dirname(__file__), "rsc", "config-missing-tool.yaml"),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_missing_tool_dependency(init_statick):
    """
    Test that a tool plugin results in failure when its dependency is not configured to run.

    Expected results: issues is None and success is False
    """
    cttp = ClangTidyToolPlugin()
    if not cttp.command_exists("clang-tidy"):
        pytest.skip("Can't find clang-tidy, unable to test clang-tidy plugin")
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--force-tool-list",
        "clang-tidy",
        "--config",
        os.path.join(
            os.path.dirname(__file__), "rsc", "config-missing-tool-dependency.yaml"
        ),
    ]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_tool_dependency(init_statick):
    """
    Test that a tool plugin can run its dependencies.

    Expected results: issues is None and success is False
    """
    cttp = ClangTidyToolPlugin()
    if not cttp.command_exists("clang-tidy"):
        pytest.skip("Can't find clang-tidy, unable to test clang-tidy plugin")
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--config",
        os.path.join(
            os.path.dirname(__file__), "rsc", "config-enabled-dependency.yaml"
        ),
        "--force-tool-list",
        "clang-tidy",
    ]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    for tool in issues:
        assert not issues[tool]
    assert success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_discovery_dependency(init_statick):
    """
    Test that a discovery plugin can run its dependencies.

    Expected results: issues is None and success is False
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--config",
        os.path.join(
            os.path.dirname(__file__), "rsc", "config-discovery-dependency.yaml"
        ),
    ]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    _, success = statick.run(path, parsed_args)
    assert success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_no_reporting_plugins(init_statick):
    """
    Test that no reporting plugins returns unsuccessful.

    Expected results: issues is None and success is False
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--config",
        os.path.join(
            os.path.dirname(__file__), "rsc", "config-no-reporting-plugins.yaml"
        ),
    ]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_invalid_reporting_plugins(init_statick):
    """
    Test that invalid reporting plugins returns unsuccessful.

    Expected results: issues is None and success is False
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--config",
        os.path.join(
            os.path.dirname(__file__), "rsc", "config-invalid-reporting-plugins.yaml"
        ),
    ]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_invalid_level(init_statick):
    """
    Test that invalid profile results in invalid level.

    Expected results: issues is None and success is False
    """
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--profile",
        os.path.join(os.path.dirname(__file__), "rsc", "nonexistent.yaml"),
    ]
    args.output_directory = os.path.dirname(__file__)
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


@mock.patch("os.mkdir")
def test_run_mkdir_oserror(mocked_mkdir, init_statick):
    """
    Test the behavior when mkdir in run throws an OSError.

    Expected results: issues is None and success is False
    """
    mocked_mkdir.side_effect = OSError("error")
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--path",
        os.path.dirname(__file__),
        "--output-directory",
        os.path.dirname(__file__),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, success = statick.run(path, parsed_args)
    assert issues is None
    assert not success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


def test_run_file_cmd_does_not_exist(init_statick):
    """
    Test when file command does not exist.

    Expected results: no issues found even though Python file without extension does
    have issues
    """
    with modified_environ(PATH=""):
        args = Args("Statick tool")
        args.parser.add_argument("--path", help="Path of package to scan")

        statick = Statick(args.get_user_paths())
        statick.gather_args(args.parser)
        sys.argv = [
            "--path",
            os.path.join(os.path.dirname(__file__), "test_package"),
            "--output-directory",
            os.path.dirname(__file__),
            "--force-tool-list",
            "pylint",
        ]
        parsed_args = args.get_args(sys.argv)
        path = parsed_args.path
        statick.get_config(parsed_args)
        statick.get_exceptions(parsed_args)
        issues, success = statick.run(path, parsed_args)
    for tool in issues:
        assert not issues[tool]
    assert success
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "test_package-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))


@mock.patch("subprocess.check_output")
def test_run_called_process_error(mock_subprocess_check_output):
    """
    Test running Statick when each plugin has a CalledProcessError.

    Expected result: issues is None
    """
    mock_subprocess_check_output.side_effect = subprocess.CalledProcessError(
        1, "", output="mocked error"
    )
    args = Args("Statick tool")
    args.parser.add_argument("--path", help="Path of package to scan")

    statick = Statick(args.get_user_paths())
    statick.gather_args(args.parser)
    sys.argv = [
        "--output-directory",
        os.path.dirname(__file__),
        "--path",
        os.path.dirname(__file__),
    ]
    parsed_args = args.get_args(sys.argv)
    path = parsed_args.path
    statick.get_config(parsed_args)
    statick.get_exceptions(parsed_args)
    issues, _ = statick.run(path, parsed_args)
    for tool in issues:
        assert not issues[tool]
    try:
        shutil.rmtree(os.path.join(os.path.dirname(__file__), "statick-sei_cert"))
    except OSError as ex:
        print("Error: {}".format(ex))
