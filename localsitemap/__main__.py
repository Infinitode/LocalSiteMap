"""Allow ``python -m localsitemap`` to behave like the ``localsitemap`` CLI."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
