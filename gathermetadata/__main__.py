#!/usr/bin/env python
# encoding: utf8

# beNNch - Unified execution, collection, analysis and
# comparison of neural network simulation benchmarks.
# Copyright (C) 2021 Forschungszentrum Juelich GmbH, INM-6

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.  You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# SPDX-License-Identifier: GPL-3.0-or-later
"""
Collector for generic metadata of HPC execution environment.

Usage: gathermetadata [options] <outdir>

Options:
    -v, --verbose       increase output
    -h, --help          print this text
"""
import logging
import logging.config
import shlex
import time
from pathlib import Path
from pprint import pformat
from subprocess import DEVNULL, PIPE, CalledProcessError, Popen, TimeoutExpired
from typing import Dict

from docopt import docopt  # type: ignore

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger()

try:
    import yaml

    basepath = Path(__file__).parent
    with (basepath / "../logging.yaml").open("r", encoding="utf8") as logconfig:
        logging.config.dictConfig(yaml.safe_load(logconfig))
except ImportError as exc:
    logging.basicConfig(level=logging.DEBUG)
    log.warning("using basic logging config due to exception %s", exc)
except FileNotFoundError as exc:
    logging.basicConfig(level=logging.DEBUG)
    log.warning("using basic logging config due to exception %s", exc)

_recordables = {
    "date": "date --iso=seconds",
    "lshw": "lshw -json -quiet",
    "dmidecode": "dmidecode",
    "lspci": "lspci -v",
    "false": "/bin/false",
    "broken": "nothing",
    "cpuinfo": "cat /proc/cpuinfo",
    "meminfo": "cat /proc/meminfo",
    "env-vars": "/usr/bin/env",
    "ldd-nest": "ldd nest",
    "conda-environment": "conda env export",
    "hostname": "hostname -f",
    "ompi_info": "ompi_info",
    "ip-r": "ip r",
    "ip-l": "ip l",
    "nproc": "nproc",
    "hwloc-info": "hwloc-info",
    "hwloc-ls": "hwloc-ls",
    # 'hwloc-topology': 'hwloc-gather-topology {outdir}/hwloc-topology',
    "lstopo": "lstopo --of ascii {outdir}/{name}",
    "getconf": "getconf -a",
    "ulimit": "ulimit -a",
    "modules": "module list",
    "ps-aux": "ps aux",
    "scontrol": "scontrol show jobid ${SLURM_JOBID} -d",
    "mpivars": "mpivars",
}


class Recorder:
    "Record metadata and handle all error cases."

    def __init__(self, outdir: str = "about", timeout: int = 3, errors_fatal: bool = False):
        self.errors_fatal = errors_fatal
        self.timeout = timeout
        self.logtimethres = 10  # seconds
        self.outdir = Path(outdir or ".")
        if not self.outdir.is_dir():
            self.outdir.mkdir()
            log.warning("created output directory %s", outdir)

    def __make_command(self, name, command):
        "Build a Popen compatible list to run the command."
        parameters = {
            "outdir": self.outdir,
            "name": name,
            "command": command,
        }
        return shlex.split(command.format(**parameters))

    def record(self, name: str, command: str):
        "Record output of a single command."
        log.info("recording %s...", name)

        starttime = time.time()
        stoptime = None
        iotime = None
        try:
            with Popen(self.__make_command(name, command), stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as infile:
                try:
                    (stdout_data, stderr_data) = infile.communicate(timeout=self.timeout)
                except TimeoutExpired:
                    log.warning("%s: process did not finish in time! Output will be incomplete!", name)
                    infile.kill()
                    outs, errs = infile.communicate()
                    log.error("Final words on stdout:\n%s", outs)
                    log.error("Final words on stderr:\n%s", errs)
                stoptime = time.time()
                if infile.returncode != 0:
                    log.warning("%s: returned %s (non-zero)!", name, infile.returncode)
                with open(self.outdir / (name + ".out"), "wb") as outfile:
                    outfile.write(stdout_data)
                if stderr_data:
                    with open(self.outdir / (name + ".err"), "wb") as errfile:
                        log.warning("ERRORS recorded for %s", name)
                        errfile.write(stderr_data)
                        if self.errors_fatal:
                            log.fatal("ERRORS are configured to be fatal.")
                            raise ValueError("Process wrote errors to STDERR!")
                iotime = time.time()
        except CalledProcessError as e:
            log.error("%s: called process failed! retrun code: %d", name, e.returncode)
        except FileNotFoundError as e:
            log.error("%s: %s", name, e)
        finally:
            if stoptime and starttime and stoptime - starttime > self.logtimethres:
                log.info("%s execution took %s seconds", name, stoptime - starttime)
            if iotime and stoptime and iotime - stoptime > self.logtimethres:
                log.info("%s io took %s seconds", name, stoptime - starttime)

    def record_all(self, recordables: Dict[str, str]):
        "Iterate through all recordables and gather data safely."
        for recordable in recordables.items():
            self.record(*recordable)


def main():
    "Start main CLI entry point."
    args = docopt(__doc__)
    if args["--verbose"]:
        log.setLevel(logging.DEBUG)
    log.debug(pformat(args))

    log.info("Gathering metadata...")
    recorder = Recorder(outdir=args["<outdir>"])
    recorder.record_all(_recordables)


if __name__ == "__main__":
    main()
