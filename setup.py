"""
ins is a command-line client for Insight
"""
from setuptools import find_packages, setup

dependencies = ['click']

setup(
    name='ins',
    version='0.1.0',
    url='https://github.com/ollybritton/python-ins',
    license='BSD',
    author='Olly Britton',
    author_email='ollybritton@gmail.com',
    description='ins is a command-line client for Insight',
    long_description=__doc__,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'ins = ins.cli:run',
        ],
    },
)
