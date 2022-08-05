from cython_tools.logs import log
import os
import shutil


def make_samples(project_root):
    sample_project_dir = '_cy_tools_samples'
    samples_project_source = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', sample_project_dir)

    assert os.path.exists(samples_project_source), f'samples_project_source path does not exist: {samples_project_source}'
    assert os.path.exists(project_root), f'project root does not exist: {project_root}'

    samples_project_dest = os.path.join(project_root, sample_project_dir)

    if os.path.exists(samples_project_dest):
        raise FileExistsError(f'samples_project_dest already exists: {samples_project_dest}')

    log.info(f'Creating sample project at: {samples_project_dest}')
    shutil.copytree(samples_project_source, samples_project_dest)

