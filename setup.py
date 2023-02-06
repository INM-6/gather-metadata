# encoding: utf8
'Packaging configuration.'

from setuptools import setup        # type: ignore

with open("README.md", encoding="utf8") as infile:
    long_description = infile.read()

install_requires = [
    'GitPython',
    'docopt-ng',
    'ruamel.yaml',
]

setup(
    name="Gather Metadata",
    version='0.1.0',
    packages=['gathermetadata'],
    package_data={
        '': [
            'LICENSE'
        ],
    },

    install_requires=install_requires,

    author="Dennis Terhorst",
    author_email="d.terhorst@fz-juelich.de",
    description="Put a one-or-two sentence summary description here.",
    long_description=long_description,

    entry_points={
        'console_scripts': [
            'gathermetadata = gathermetadata.__main__:main',
        ],
    },

    license="GPL-3.0-only",

    url='https://github.com/INM-6/gather-metadata',
    # https://pypi.org/pypi?:action=list_classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: {'name': 'GNU General Public License v3.0 only', 'spdx': 'GPL-3.0-only'}',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering']
)
