#!/usr/bin/env python3
"""Verify that every file of a PyPI release carries PEP 740 provenance.

The script talks to the public PyPI Integrity API:

    https://pypi.org/integrity/{project}/{version}/{filename}/provenance

For each distribution file of the given release it checks that at least one
attestation bundle is present and prints the trusted publisher identity the
attestations are bound to. This is what makes the "provenance" indicator on
the PyPI project page show up, so the release workflow runs it after every
upload.

Exit codes:
    0 - every file is attested (or --allow-missing was given)
    1 - at least one file has no provenance
    2 - the release could not be queried at all

Usage:
    python .github/scripts/verify_provenance.py --project localsitemap --version 2.1.0
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

PYPI_JSON = "https://pypi.org/pypi/{project}/{version}/json"
PYPI_INTEGRITY = "https://pypi.org/integrity/{project}/{version}/{filename}/provenance"
USER_AGENT = "localsitemap-release-check/1.0"


def _get_json(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _release_files(project, version):
    data = _get_json(PYPI_JSON.format(project=project, version=version))
    return [item["filename"] for item in data.get("urls", [])]


def _provenance(project, version, filename):
    url = PYPI_INTEGRITY.format(project=project, version=version, filename=filename)
    try:
        return _get_json(url)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _describe(bundles):
    descriptions = []
    for bundle in bundles:
        publisher = bundle.get("publisher") or {}
        parts = [
            str(publisher.get("kind", "unknown")),
            str(publisher.get("repository", "")),
            str(publisher.get("workflow", "")),
        ]
        environment = publisher.get("environment")
        if environment:
            parts.append("env=%s" % environment)
        descriptions.append(" ".join(part for part in parts if part))
    return "; ".join(descriptions)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="localsitemap")
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="do not fail when a file has no provenance",
    )
    parser.add_argument(
        "--attempts", type=int, default=5,
        help="how many times to retry while PyPI propagates a new release",
    )
    parser.add_argument("--delay", type=float, default=6.0, help="seconds between retries")
    args = parser.parse_args(argv)

    filenames = []
    for attempt in range(1, max(1, args.attempts) + 1):
        try:
            filenames = _release_files(args.project, args.version)
            if filenames:
                break
        except (urllib.error.URLError, ValueError) as error:
            print("could not query PyPI (%s), attempt %d" % (error, attempt))
        if attempt < args.attempts:
            time.sleep(args.delay)

    if not filenames:
        print(
            "error: no files found for %s %s on PyPI" % (args.project, args.version),
            file=sys.stderr,
        )
        return 2

    missing = []
    for filename in filenames:
        data = None
        for attempt in range(1, max(1, args.attempts) + 1):
            try:
                data = _provenance(args.project, args.version, filename)
                if data:
                    break
            except (urllib.error.URLError, ValueError) as error:
                print("  %s: query failed (%s), attempt %d" % (filename, error, attempt))
            if attempt < args.attempts:
                time.sleep(args.delay)

        bundles = (data or {}).get("attestation_bundles") or []
        if bundles:
            print("OK   %s -> %s" % (filename, _describe(bundles)))
        else:
            print("MISS %s has no provenance on PyPI" % filename)
            missing.append(filename)

    if missing:
        if args.allow_missing:
            print("warning: %d file(s) without provenance" % len(missing))
            return 0
        print(
            "error: %d file(s) were published without provenance: %s"
            % (len(missing), ", ".join(missing)),
            file=sys.stderr,
        )
        return 1

    print("All %d file(s) are attested with verifiable provenance." % len(filenames))
    return 0


if __name__ == "__main__":
    sys.exit(main())
