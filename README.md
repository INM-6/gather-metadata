
# Gather Metadata

Collector for generic metadata of HPC execution environment focussed on
benchmarking.


## Installation

Currently the tool is not publicly available on PyPi and is installed directly
from the repository. It is recommended to install the package into an
environment. For example using Python `venv` could be done as follows:

```bash
python -m venv venv
source venv/bin/activate
pip install -U pip
pip install git+ssh://git@github.com/INM-6/gather-metadata.git
```

If SSH is not available, use
`git+https://$TOKEN@github.com/INM-6/gather-metadata.git` together with a
GitHub Personal Access Token (PAT).


## Usage

Running the tool with a directory name will create that directory and gather
all information into it. You can nicely zip it and store it together with the
other result data. The intermediate folder is not needed anymore, but may be
useful to already extract rudimentary first metadata to annotate the run.


```bash
gathermetadata about;
tar -czf some-run-id-or-so.tgz about && rm -rf about
```

## Customizations & Contributions

If you know about additional metadata sources please do not just customize your
fork but create a pull request to add the gathering globally in `recordables`
([here](https://github.com/INM-6/gather-metadata/blob/main/gathermetadata/__main__.py#L51)),
even if your command is extremely specific to your case or environment! The
tool will always try to gather the maximum of avilable data and skip any source
not found automatically. It has been taken great care that broken entries will
not annoy anyone.


## Development and Testing

To install in development mode add the `dev` feature flag to the `pip install`
line of the normal installation procedure:

```bash
pip install -e .[dev]
```

To run the test suite type

```bash
pytest gathermetadata
```

## License

This project is licensed under GNU General Public License v3.0 only.
See LICENSE for details.

```
SPDX-License-Identifier: GPL-3.0-only
SPDX-Copyright: 2023, Forschungszentrum Jülich GmbH, Jülich, Germany
SPDX-Author: Dennis Terhorst <d.terhorst@fz-juelich.de>
```
