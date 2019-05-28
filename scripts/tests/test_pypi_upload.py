from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict

import pytest


@dataclass
class Counts:
    """Stores call counts of various api methods and contains methods
    to help capture and validate call counts

    Attributes:
        create: expected call count for vsh.api.create
        enter: expected call count for vsh.api.enter
        remove: expected call count for vsh.api.remove
        show_venvs: expected call count for vsh.api.show_venvs
        show_version: expected call count for vsh.api.show_version

    """

    create: int = 0
    enter: int = 0
    remove: int = 0
    show_venvs: int = 0
    show_version: int = 0

    def check(self) -> Dict[str, bool]:
        """Returns a dictionary of boolean which represents whether or
        not the actual call counts matched the expected call counts.
        """
        import vsh.api

        counts = {
            method_name: getattr(vsh.api, method_name).call_count == expected_call_count
            for method_name, expected_call_count in asdict(self).items()
        }
        return counts

    def mock_all(self, mocker, venv_path: Path, exit_code: int = 0):
        """Mocks all tracked api methods

        Args:
            mocker: pytest-mock's mocker fixture
            venv_path: path to virtual environment under test
            exit_code: the expected exit code of the vsh.api.enter call
        """
        self.mock_create(mocker=mocker, venv_path=venv_path)
        self.mock_enter(mocker=mocker, exit_code=exit_code)
        self.mock_remove(mocker=mocker, venv_path=venv_path)
        self.mock_show_venvs(mocker=mocker)
        self.mock_show_version(mocker=mocker)

    def mock_create(self, mocker, venv_path: Path):
        mocker.patch("vsh.api.create", return_value=venv_path)

    def mock_enter(self, mocker, exit_code: int = 0):
        mocker.patch("vsh.api.enter", return_value=exit_code)

    def mock_remove(self, mocker, venv_path: Path):
        mocker.patch("vsh.api.remove", return_value=venv_path)

    def mock_show_venvs(self, mocker):
        mocker.patch("vsh.api.show_venvs")

    def mock_show_version(self, mocker):
        mocker.patch("vsh.api.show_version")


# ######################################################################
@dataclass
class CleanupTestCase:
    venv_path: Path = field(default_factory=Path)
    repo_path: Path = field(default_factory=Path)
    verbose: int = 0
    counts: Counts = field(default_factory=Counts)

    @property
    def kwds(self):
        kwds = asdict(self)
        kwds.pop("counts")
        return kwds


@pytest.mark.parametrize("test_case", [CleanupTestCase(counts=Counts(remove=1))])
def test_cleanup(test_case, venv_path, repo_path, mocker):
    import shutil  # noqa
    from ..pypi_upload import cleanup

    test_case.venv_path = venv_path
    test_case.repo_path = repo_path

    test_case.counts.mock_all(mocker=mocker, venv_path=venv_path)
    mocker.patch("shutil.rmtree")
    cleanup(**test_case.kwds)

    checked = test_case.counts.check()
    assert all(checked.values())


# ######################################################################
@dataclass
class CreateDistTestCase:
    venv_path: Path = field(default_factory=Path)
    verbose: int = 0
    counts: Counts = field(default_factory=Counts)

    @property
    def kwds(self):
        kwds = asdict(self)
        kwds.pop("counts")
        return kwds


@pytest.mark.parametrize("test_case", [CreateDistTestCase(counts=Counts(enter=1))])
def test_create_distribution(test_case, venv_path, mocker):
    from ..pypi_upload import create_distribution

    test_case.venv_path = venv_path

    test_case.counts.mock_all(mocker=mocker, venv_path=venv_path)
    create_distribution(**test_case.kwds)

    checked = test_case.counts.check()
    assert all(checked.values())


# ######################################################################
@dataclass
class FindMatchedGpgTestCase:
    repo_path: Path = field(default_factory=Path)
    counts: Counts = field(default_factory=Counts)

    @property
    def kwds(self):
        kwds = asdict(self)
        kwds.pop("counts")
        return kwds


@pytest.mark.parametrize("test_case", [FindMatchedGpgTestCase()])
def test_find_matched_gpg(test_case, repo_path, venv_path, mocker):
    from ..pypi_upload import find_matched_gpg

    test_case.repo_path = repo_path

    test_case.counts.mock_all(mocker=mocker, venv_path=venv_path)
    find_matched_gpg(**test_case.kwds)

    checked = test_case.counts.check()
    assert all(checked.values())


# ######################################################################
@dataclass
class SetupVenvTestCase:
    venv_path: Path = field(default_factory=Path)
    repo_path: Path = field(default_factory=Path)
    verbose: int = 0
    counts: Counts = field(default_factory=Counts)

    @property
    def kwds(self):
        kwds = asdict(self)
        kwds.pop("counts")
        return kwds


@pytest.mark.parametrize("test_case", [SetupVenvTestCase(counts=Counts(create=1, enter=2))])
def test_setup_venv(test_case, repo_path, venv_path, mocker):
    from ..pypi_upload import setup_venv

    mocker.patch("shutil.rmtree")
    test_case.repo_path = repo_path

    test_case.counts.mock_all(mocker=mocker, venv_path=venv_path)
    setup_venv(**test_case.kwds)

    checked = test_case.counts.check()
    assert all(checked.values())


# ######################################################################
@dataclass
class RunTestsTestCase:
    venv_path: Path = field(default_factory=Path)
    verbose: int = 0
    counts: Counts = field(default_factory=Counts)

    @property
    def kwds(self):
        kwds = asdict(self)
        kwds.pop("counts")
        return kwds


@pytest.mark.parametrize("test_case", [RunTestsTestCase(counts=Counts(enter=1))])
def test_run_tests(test_case, venv_path, mocker):
    from ..pypi_upload import run_tests

    test_case.venv_path = venv_path

    test_case.counts.mock_all(mocker=mocker, venv_path=venv_path)
    run_tests(**test_case.kwds)

    checked = test_case.counts.check()
    assert all(checked.values())


# ######################################################################
@dataclass
class UploadDistTestCase:
    venv_path: Path = field(default_factory=Path)
    repo_path: Path = field(default_factory=Path)
    prod: bool = False
    verbose: int = 0
    matched_dist_file_path: Path = field(default_factory=Path)
    matched_gpg_path: Path = field(default_factory=Path)
    counts: Counts = field(default_factory=Counts)

    @property
    def kwds(self):
        kwds = asdict(self)
        kwds.pop("counts")
        kwds.pop("matched_dist_file_path")
        kwds.pop("matched_gpg_path")
        return kwds


@pytest.mark.parametrize(
    "test_case",
    [
        UploadDistTestCase(
            matched_dist_file_path=Path("/tmp/dist-path"),
            matched_gpg_path=Path("/tmp/gpg_path"),
            prod=False,
            counts=Counts(enter=1),
        ),
        UploadDistTestCase(
            matched_dist_file_path=Path("/tmp/dist-path"),
            matched_gpg_path=Path("/tmp/gpg_path"),
            prod=True,
            counts=Counts(enter=1),
        ),
    ],
)
def test_upload_distribution(test_case, repo_path, venv_path, mocker):
    from ..pypi_upload import find_matched_gpg, upload_distribution

    mocker.patch(
        "scripts.pypi_upload.find_matched_gpg",
        return_value=(test_case.matched_dist_file_path, test_case.matched_gpg_path),
    )

    test_case.venv_path = venv_path
    test_case.venv_path = repo_path

    test_case.counts.mock_all(mocker=mocker, venv_path=venv_path)
    upload_distribution(**test_case.kwds)

    find_matched_gpg.call_count = 1
    checked = test_case.counts.check()
    assert all(checked.values())
