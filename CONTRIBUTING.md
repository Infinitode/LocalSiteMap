# Contributing to LocalSiteMap

Thank you for considering contributing to **LocalSiteMap**! Contributions, whether they are bug fixes, new features, or improvements to the documentation, are always welcome. Before contributing, please read the following guidelines to ensure smooth collaboration.

## Getting Started

1. **Fork the Repository**
   Create a fork of this repository to your GitHub account and clone it locally.

2. **Set Up the Environment**
   Ensure you have Python 3.9+ installed. LocalSiteMap has no runtime dependencies, so there is nothing else to install for development (a virtual environment is still recommended).

3. **Run Tests**
   Before making changes, run tests to confirm that everything works:

   ```bash
   python -m unittest -v test_localsitemap
   ```

   The same suite runs on GitHub Actions for Python 3.9 – 3.14 on Linux, plus Windows.

> [!TIP]
> We sometimes include testing scripts in our projects for easy testing. `test.py` is a small manual demo you can point at any directory.

## How to Contribute

1. **Report Issues**
   Use the [GitHub Issues page](https://github.com/Infinitode/LocalSiteMap/issues) to report bugs or suggest features. Please include:
   - A clear description of the issue or suggestion.
   - Steps to reproduce (for bugs).

2. **Make Changes**
   - Use clear and descriptive commit messages.
   - (Optional) Write tests to show new functionality.
   - Ensure the code is **readable**. You can learn more about Python code readability here: https://peps.python.org/pep-0008/.

3. **Submit a Pull Request**
   - Push your changes to a feature branch in your fork.
   - Submit a pull request with a detailed explanation of what you've changed or added.
   - Ensure your PR passes all automated tests and adheres to the contribution guidelines.

## Building Locally

All project metadata lives in `pyproject.toml`, and the version is read from `localsitemap/_version.py`.

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check --strict dist/*
```

## Releasing

1. Update `__version__` in `localsitemap/_version.py` and the changelog in `README.md`.
2. Commit and push, then push a matching tag (`2.1.0` or `v2.1.0`):

   ```bash
   git tag 2.1.0
   git push origin 2.1.0
   ```

3. The `Publish Python 🐍 distributions 📦 to PyPI` workflow builds the sdist and wheel, runs the tests, and publishes to PyPI using **Trusted Publishing** — no API token or repository secret is required.

   The publisher configured on PyPI must match this repository:

   | Field | Value |
   | --- | --- |
   | Owner / Repository | `Infinitode/LocalSiteMap` |
   | Workflow | `build_and_publish.yml` |
   | Environment | *(leave blank — the workflow does not set `environment:`)* |

4. The workflow signs every uploaded file with a PEP 740 attestation and then runs `.github/scripts/verify_provenance.py`, which fails the release if any published file is missing provenance. That is what makes the provenance badge and the PyPI "provenance" indicator accurate.

## Community Guidelines

To maintain a positive and collaborative community, we ask that all contributors adhere to the following principles:

1. **Be Respectful**
   Treat others with respect, regardless of their background or expertise.

2. **Provide Constructive Feedback**
   Offer helpful and actionable suggestions during code reviews.

3. **Follow Licensing Requirements**
   Ensure that any derivative works comply with the [license](https://github.com/Infinitode/LocalSiteMap/blob/main/LICENSE).

By contributing, you agree to abide by these guidelines and this project's [license](https://github.com/Infinitode/LocalSiteMap/blob/main/LICENSE). Thank you for helping make **LocalSiteMap** better!
