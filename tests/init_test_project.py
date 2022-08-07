from cython_tools.building import initialize, build
import shutil
import os
import sys
import Cython
import subprocess

if __name__ == '__main__':
    proj_root = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'init_project')
    if os.path.exists(proj_root):
        shutil.rmtree(proj_root)

    initialize(proj_root,
               verbosity=3,
               include_samples=True,
               include_boilerplate=True,
               boilerplate_name='cytoolzz',
               )
    os.putenv()
    build(proj_root, is_debug=True, annotate=True)

    shutil.copy(os.path.join(os.path.dirname(__file__), '..', 'src', 'cython_tools', '_boilerplate_package', 'cytools_script.py'),
                os.path.join(proj_root, 'cytool'))

    subprocess.call(['chmod', '+x', os.path.join(proj_root, 'cytool')])