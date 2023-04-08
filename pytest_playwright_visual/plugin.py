import sys
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
import pytest
from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch


@pytest.fixture
def assert_snapshot(pytestconfig: Any, request: Any, browser_name: str) -> Callable:
    test_name = f"{str(Path(request.node.name))}[{str(sys.platform)}]"
    test_dir = str(Path(request.node.name)).split('[', 1)[0]

    def compare(img: bytes, *, threshold: float = 0.1, name=f'{test_name}.png', fail_fast=False) -> None:
        update_snapshot = pytestconfig.getoption("--update-snapshots")
        force_update_snapshot = pytestconfig.getoption(
            "--update-snapshots-forceall")
        test_file_name = str(os.path.basename(
            Path(request.node.fspath))).strip('.py')
        filepath = (
            Path(request.node.fspath).parent.resolve()
            / 'snapshots'
            / test_file_name
            / test_dir
        )
        filepath.mkdir(parents=True, exist_ok=True)
        file = filepath / name
        # Create a dir where all snapshot test failures will go
        results_dir_name = (Path(request.node.fspath).parent.resolve()
                            / "snapshot_tests_failures")
        snapshot_name = name.split('.')[0]
        test_results_dir = (results_dir_name
                            / test_file_name / test_name / snapshot_name)

        # Remove a snapshots past run dir with actual, diff and expected images
        previous_failure = test_results_dir.exists()
        if previous_failure:
            shutil.rmtree(test_results_dir)

        # If force updating them can do straight away
        if force_update_snapshot:
            file.write_bytes(img)
            print(f'Force updated: {name}')
            return

        # Only update in case a previous failure was registered
        # This guards against the case where a test finishes early and
        # we dont get a chance to see a snapshot which was due to fail
        # If no previous failure was registered then it will attempt to diff
        # the image and sucessfully raise an error for us to review
        if update_snapshot and previous_failure:
            file.write_bytes(img)
            print(f'Updated: {name}')
            return
            # pytest.fail(f'Updated: {name}', pytrace=False)

        if not file.exists():
            file.write_bytes(img)
            print(f'Created: {name}')
            return
            # pytest.fail(f'Created: {name}', pytrace=False)

        # This will happen in case in all other cases
        img_a = Image.open(BytesIO(img))
        img_b = Image.open(file)
        img_diff = Image.new("RGBA", img_a.size)
        try:
            mismatch = pixelmatch(img_a, img_b, img_diff,
                                  threshold=threshold, fail_fast=fail_fast)
        except ValueError as e:
            # Save failed image
            test_results_dir.mkdir(parents=True, exist_ok=True)
            img_a.save(f'{test_results_dir}/Failed_{name}')
            # Raise original error
            raise e

        if mismatch == 0:
            return
        else:
            # Create new test_results folder
            test_results_dir.mkdir(parents=True, exist_ok=True)
            img_diff.save(f'{test_results_dir}/Diff_{name}')
            img_a.save(f'{test_results_dir}/Actual_{name}')
            img_b.save(f'{test_results_dir}/Expected_{name}')
            pytest.fail(f'DOES NOT MATCH: {name}', pytrace=False)

    return compare


def pytest_addoption(parser: Any) -> None:
    group = parser.getgroup("playwright-snapshot", "Playwright Snapshot")
    group.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Update snapshots.",
    )
    group.addoption(
        "--update-snapshots-forceall",
        action="store_true",
        default=False,
        help="Update snapshots.",
    )
