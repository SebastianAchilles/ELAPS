#!/usr/bin/env python
"""Wrapper for ELAPS:Viewer."""
from __future__ import division, print_function

from .. import defines
from ..qt import Viewer

import argparse


def main():
    """Main entry point."""
    # parse args
    parser = argparse.ArgumentParser(
        description="ELAPS Viewer (Report GUI)"
    )
    parser.add_argument("--reset", action="store_true",
                        help="reset to default Experiment")
    parser.add_argument("report",  nargs="*",
                        help="ELAPS Report (.%s)" % defines.report_extension)
    args = parser.parse_args()

    # start Viewer
    Viewer(*args.report, reset=args.reset).start()


if __name__ == "__main__":
    main()
