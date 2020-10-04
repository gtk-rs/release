from setuptools import find_packages, setup
from src import __version__, __author__

setup(
    name='release',
    version=__version__,
    author=__author__,
    url='https://github.com/gtk-rs/release',
    description='Release script',
    package_dir={'src': 'src'},
    packages=find_packages(),
    scripts=[
        'src/release.py',
    ],
    install_requires=[
        'datetime',
        'requests',
        'toml',
    ]
)
