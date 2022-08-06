import os
import shutil
import sys
from typing import Union, List
from cython_tools.logs import log
from cython_tools.common import check_project_initialized
from setuptools import Extension, setup
import numpy as np
from Cython.Build import cythonize
import importlib.util
import glob
from unittest import mock
import io
from .annotate_templates import TEMPLATE_PACKAGE, TEMPLATE_URL, TEMPLATE_ANNOTATE_INDEX
from cython_tools.common import open_url_in_browser
import webbrowser
import subprocess

def annotate_command(args):
    """
    Main entry point for shell command
    """
    log.setup('cython_tools__annotate', verbosity=args.verbose)

    annotate_idx_fn = annotate(
            args.annotate_target,
            project_root=args.project_root,
            force=args.force,
            append=args.append,
    )
    if args.browser:
        open_url_in_browser(f'file://{annotate_idx_fn}')
    else:
        print(f'file://{annotate_idx_fn}')


def annotate(
            pyx_file_or_list: Union[str, List[str], None] = None,
            project_root: str = None,
            force = False,
            append = False,
            ):
    """
    In normal circumstances this command will be called after build --annotate
    :param pyx_file_or_list:
    :param project_root:
    :return:
    """

    # Check if cython tools in a good state in the project root
    project_root, cython_tools_path = check_project_initialized(project_root)
    log.info(f'Starting annotation at {project_root}')

    def get_pyx_html(fn):
        _fn = os.path.abspath(fn)
        if not os.path.exists(_fn):
            raise FileNotFoundError(f'.pyx file not found: {_fn}')
        if not _fn.endswith('.pyx'):
            raise ValueError(f'{_fn} must end with .pyx')
        if not _fn.startswith(project_root):
            raise ValueError(f'{_fn} not in project root!')
        log.trace(f' >>> Adding: {_fn}')
        return _fn, _fn[:-4] + '.html'

    log.debug('Preparing .pyx file list for annotations')
    is_singe_file = False
    if pyx_file_or_list is None:
        pyx_file_or_list = glob.glob(os.path.join(project_root, '**', '*.pyx'), recursive=True)
    elif isinstance(pyx_file_or_list, str):
        if os.path.isdir(pyx_file_or_list):
            pyx_file_or_list = glob.glob(os.path.join(pyx_file_or_list, '**', '*.pyx'), recursive=True)
        else:
            _single_filename = pyx_file_or_list
            pyx_file_or_list = [_single_filename]
            is_singe_file = True

    annotations_path = os.path.join(cython_tools_path, 'annotations')
    if not is_singe_file:
        # Cleanup annotations folder
        if not append:
            if os.path.exists(annotations_path):
                log.debug(f'Rewriting {annotations_path}')
                shutil.rmtree(annotations_path)
        else:
            log.debug(f'Appending new to {annotations_path}')
        os.makedirs(annotations_path, exist_ok=True)

    html_files = [get_pyx_html(fn) for fn in pyx_file_or_list]

    annotation_index_path = os.path.join(cython_tools_path, 'annotation_index.html')

    for pyx_fn, html_fn in html_files:
        assert project_root in pyx_fn, f'{pyx_fn} does not belong to project root'
        f_rel_path = html_fn.replace(project_root, '')
        if f_rel_path.startswith(os.path.sep):
            # If f_rel_path starts with /, the os.path.join wouldn't work as expected
            f_rel_path = f_rel_path[1:]
        annotate_html_file = os.path.join(annotations_path, f_rel_path)

        c_fn = pyx_fn[:-4] + '.c'

        if os.path.exists(c_fn + '.ctools'):
            # Cleanup old ctools backups (maybe kept after crashes)
            os.unlink(c_fn + '.ctools')

        if not os.path.exists(html_fn) or force or is_singe_file:
            log.trace(f'Annotating: {html_fn}')
            if os.path.exists(c_fn):
                # Preserve old source just in case if it has compiled with different flags
                shutil.move(c_fn, c_fn+'.ctools')

            os.system(f'cython --annotate {pyx_fn}')

            # Delete new .c file, and replace with backup
            os.unlink(c_fn)
            if os.path.exists(c_fn+'.ctools'):
                shutil.move(c_fn + '.ctools', c_fn)

            assert os.path.exists(html_fn), f'No annotations was generated from {pyx_fn}'
        else:
            log.trace(f'Using existing annotation: {html_fn}')

        # Move file to annotations
        if not is_singe_file:
            log.trace(f'Copy: {html_fn} to {annotate_html_file}')
            os.makedirs(os.path.dirname(annotate_html_file), exist_ok=True)
            shutil.copy(html_fn, annotate_html_file)
        else:
            # Don't move annotated file, just use is as single index
            annotation_index_path = html_fn

    if is_singe_file:
        return annotation_index_path
    else:
        return build_annotation_index(annotation_index_path)

def build_package_links(pkg_path, relative_path, only_files = False):
    str_buf = io.StringIO()

    if only_files:
        dirlist = []
    else:
        dirlist = list(sorted([x for x in os.listdir(pkg_path) if os.path.isdir(os.path.join(pkg_path, x))]))
    filelist = list(sorted([x for x in os.listdir(pkg_path) if not os.path.isdir(os.path.join(pkg_path, x))]))

    for d in (dirlist + filelist):
        str_buf.write('<li>\n')
        _abs_path = os.path.join(pkg_path, d)

        if os.path.isdir(_abs_path):
            str_buf.write(f'{d}\n')
            str_buf.write(build_package_links(_abs_path, os.path.join(relative_path, d)))
        elif _abs_path.endswith('.html'):
            str_buf.write(TEMPLATE_URL.substitute(
                    url=os.path.join(relative_path, d).replace('\\', '/'),
                    label=d.replace('.html', '.pyx')
            ))

        str_buf.write('</li>\n')
    buf_str = str_buf.getvalue()
    if buf_str:
        return f'<ul>\n{buf_str}</ul>\n'
    else:
        return f''


def build_annotation_index(annotation_index_path):
    log.debug(f'Building annotation index file in {annotation_index_path}')
    cython_tools_path = os.path.dirname(annotation_index_path)
    annotations_path = os.path.join(cython_tools_path, 'annotations')

    accordion_buff = io.StringIO()
    #
    # Try to process folders first
    #
    for d in sorted(os.listdir(annotations_path)):
        pkg_name = d
        pkg_path = os.path.join(annotations_path, d)
        if not os.path.isdir(pkg_path):
            continue
        log.trace(f'Annotation index: processing package {pkg_name}')
        package_links = build_package_links(pkg_path, relative_path=os.path.join('annotations', d))
        if package_links:

            accordion_buff.write(TEMPLATE_PACKAGE.substitute(package_name=pkg_name.replace('/', '_').replace('.', '_'),
                                                             package_title=pkg_name,
                                                             package_contents=package_links,
                                                             ))

    package_links = build_package_links(annotations_path, relative_path=os.path.join('annotations'), only_files=True)
    if package_links:
        log.trace(f'Annotation index: processing root package')
        accordion_buff.write(TEMPLATE_PACKAGE.substitute(package_name='__cytools_project_root__',
                                                         package_title='Project root',
                                                         package_contents=package_links,
                                                         ))

    with open(annotation_index_path, 'w') as fh:
        html_str = TEMPLATE_ANNOTATE_INDEX.substitute(
                title=f'Cython tools annotation',
                accord_items=accordion_buff.getvalue(),
        )
        fh.write(html_str)

    return annotation_index_path



