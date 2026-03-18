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
    --command-timeout=<sec>     maximum time to wait for command completion
                                [default: 10]
    --log-time-threshold=<sec>  minimum time of commands to be logged
                                [default: 1]
    --errors-fatal              make any errors abort metadata gathering
    --no-result-json            do not add logging output in JSON format
    -v, --verbose               increase output
    -h, --help                  print this text
"""
import json
import logging
import logging.config
import os
import shlex
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat
from subprocess import DEVNULL, PIPE, CalledProcessError, Popen, TimeoutExpired
from typing import Any, Dict, Optional, Sequence

from docopt import docopt  # type: ignore

from . import __version__

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
    "sysctl-a": "sysctl -a",
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
    "ompi_info-parsable": "ompi_info --parsable --all",
    "lsmod": "lsmod",
    "ip-r": "ip r",
    "ip-l": "ip l",
    "nproc": "nproc",
    "numactl-show": "numactl --show",
    "numastat": "numastat",
    "lscpu-json": "lscpu --json --output-all",
    "lscpu-extended-json": "lscpu --json --output-all --bytes --extended",
    "lscpu-caches-json": "lscpu --json --output-all --bytes --caches",
    "hwloc-info": "hwloc-info",
    "hwloc-ls": "hwloc-ls",
    # hwloc-topology is extremely slow on machines with high number of cores.
    # We should consider putting this into a group of --slow commands.
    # "hwloc-topology": "hwloc-gather-topology {outdir}/hwloc-topology",
    "pip-list": "pip list --format json",
    "lstopo": "lstopo --of ascii {outdir}/{name}",
    "getconf": "getconf -a",
    "ulimit": "ulimit -a",
    "ucx_info-v": "ucx_info -v",
    "ucx_info-c": "ucx_info -c",
    "modules": "module list",
    "proc-sys-kernel": "bash -c 'cp -r /proc/sys/kernel {outdir}/{name}; chmod -R u+w {outdir}/{name}'",
    "ps-aux": "ps aux",
    "scontrol": "scontrol show jobid ${SLURM_JOBID} -d",
    "mpivars": "mpivars",
    "pldd-nest": "python -c \"import nest, subprocess as s, os; s.check_call(['/usr/bin/pldd', str(os.getpid())])\"",
}


@dataclass
class Result:  # pylint: disable=too-many-instance-attributes
    "Result metadata."

    name: str
    command: str
    starttime: float = field(default_factory=time.time)
    exectime: Optional[float] = None
    iotime: Optional[float] = None
    success: bool = False
    return_code: Optional[int] = None
    shell: Optional[Sequence[str]] = None
    stdout_file: Optional[str] = None
    stderr_file: Optional[str] = None
    error_message: Optional[str] = None


class Recorder:
    "Record metadata and handle all error cases."

    def __init__(self, outdir: str = "about", timeout: float = 3, errors_fatal: bool = False, logtimethres: float = 3):
        self.errors_fatal = errors_fatal
        self.timeout = timeout
        self.logtimethres = logtimethres  # seconds
        self.outdir = Path(outdir or ".")
        if not self.outdir.is_dir():
            self.outdir.mkdir()
            log.warning("created output directory %s", outdir)

    def __make_command(self, name, command):
        "Build a Popen compatible list to run the command."
        parameters = os.environ.copy()
        parameters.update(
            {
                "outdir": self.outdir,
                "name": name,
                "command": command,
            }
        )
        return shlex.split(command.format(**parameters))

    def _save_nonzero(self, name, data) -> Optional[str]:
        """
        Save data to file if non-zero.

        Returns
        -------
        bool:   data has been written.
        """
        filename = None
        if data:
            filename = str(self.outdir / name)
            with open(filename, "wb") as outfile:
                outfile.write(data)
        return filename

    def record(self, name: str, command: str) -> Dict[str, Any]:
        """
        Record output of a single command.

        Returns
        -------
        dict: dictionary with result metadata
        """
        log.info("recording %s...", name)

        stdout_data = None
        stderr_data = None

        res = Result(name, command)
        try:
            res.shell = self.__make_command(name, command)
            assert res.shell  # required assert, otherwise shell may be None, which is not allowed in Popen
            with Popen(res.shell, stdout=PIPE, stderr=PIPE, stdin=DEVNULL) as infile:
                try:
                    (stdout_data, stderr_data) = infile.communicate(timeout=self.timeout)
                except TimeoutExpired:
                    log.warning("%s: process did not finish in time! Output will be incomplete!", name)
                    infile.kill()
                    outs, errs = infile.communicate()
                    log.error("Final words on stdout:\n%s", outs)
                    log.error("Final words on stderr:\n%s", errs)
                    stdout_data = outs
                    stderr_data = errs
                stoptime = time.time()
                res.exectime = stoptime - res.starttime
                if infile.returncode != 0:
                    log.warning("%s: returned %s (non-zero)!", name, infile.returncode)
                res.stdout_file = self._save_nonzero(name + ".out", stdout_data)
                res.stderr_file = self._save_nonzero(name + ".err", stderr_data)
                if stderr_data and self.errors_fatal:
                    log.fatal("ERRORS are configured to be fatal.")
                    raise ValueError("Process wrote errors to STDERR!")
                res.iotime = time.time() - stoptime
                res.return_code = infile.returncode
                res.success = True
        except KeyError as e:
            log.error("%s: called process failed! Undefined variable %s", name, e)
            res.error_message = f"KeyError: Undefined variable {e}"
        except CalledProcessError as e:
            log.error("%s: called process failed! retrun code: %d", name, e.returncode)
            res.error_message = f"CalledProcessError: retrun code: {e.returncode}"
            res.return_code = e.returncode
        except FileNotFoundError as e:
            log.error("%s: %s", name, e)
            res.error_message = f"FileNotFoundError: {e}"
        finally:
            if res.exectime is not None and res.exectime > self.logtimethres:
                log.info("%s execution took %.2f seconds", name, res.exectime)
            if res.exectime is not None and res.iotime is not None and res.exectime + res.iotime > self.logtimethres:
                log.info("%s execution+io took %.2f seconds", name, res.iotime)
        return asdict(res)

    def record_all(self, recordables: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        "Iterate through all recordables and gather data safely."
        results = {}
        for recordable in recordables.items():
            results[recordable[0]] = self.record(*recordable)
        return results


def main():
    "Start main CLI entry point."
    args = docopt(__doc__)
    if args["--verbose"]:
        log.setLevel(logging.DEBUG)
    log.debug(pformat(args))

    log.info("Gathering metadata...")
    starttime = time.time()
    starttimestamp = time.ctime()

    recorder = Recorder(
        outdir=args["<outdir>"],
        logtimethres=float(args["--log-time-threshold"]),
        timeout=float(args["--command-timeout"]),
        errors_fatal=args["--errors-fatal"],
    )

    results = recorder.record_all(_recordables)

    if not args["--no-result-json"]:
        resultfile = Path(args["<outdir>"]) / "gather.json"
        log.info("writing result metadata to %s...", resultfile)
        with resultfile.open("w", encoding="utf8") as outfile:
            json.dump(
                {
                    "version": __version__,
                    "args": args,
                    "run": {
                        "start": starttime,
                        "at": starttimestamp,
                        "total_time": time.time() - starttime,
                    },
                    "results": results,
                },
                outfile,
                indent=2,
            )


if __name__ == "__main__":
    main()
