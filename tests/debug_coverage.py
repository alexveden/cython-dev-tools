from cython_dev_tools.testing import coverage

if __name__ == '__main__':
    coverage(tests_target='.',
             # project_root='./init_project'
             project_root='/home/ubertrader/cloud/code/uberhf'
             )
