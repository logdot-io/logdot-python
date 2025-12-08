# Publishing LogDot Python SDK to PyPI

This guide covers publishing the LogDot SDK (`logdot-io-sdk`) to the Python Package Index (PyPI).

## Prerequisites

1. **PyPI Account**: Create an account at [pypi.org](https://pypi.org/account/register/)
2. **TestPyPI Account** (recommended): Create at [test.pypi.org](https://test.pypi.org/account/register/)
3. **Build Tools**: Install required packages

```bash
pip install build twine
```

## Pre-Publish Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update version in `logdot/__init__.py` (`__version__`)
- [ ] Ensure versions match in both files
- [ ] Update `README.md` if needed
- [ ] Run tests: `pytest`
- [ ] Run type checker: `mypy logdot/`
- [ ] Run formatter: `black logdot/`

## Building the Package

Build source distribution and wheel:

```bash
python -m build
```

This creates two files in `dist/`:
- `logdot_io_sdk-1.0.0.tar.gz` - Source distribution
- `logdot_io_sdk-1.0.0-py3-none-any.whl` - Built wheel

## Verify Package Contents

Check the built package:

```bash
# List contents of the wheel
unzip -l dist/logdot-1.0.0-py3-none-any.whl

# Check package metadata
twine check dist/*
```

Expected contents:
- `logdot/__init__.py`
- `logdot/client.py`
- `logdot/logger.py`
- `logdot/metrics.py`
- `logdot/http.py`
- `logdot/types.py`
- `logdot/py.typed`

## Testing on TestPyPI (Recommended)

Always test on TestPyPI before publishing to production PyPI.

### Upload to TestPyPI

```bash
twine upload --repository testpypi dist/*
```

### Test Installation from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ logdot-io-sdk
```

Note: `--extra-index-url` is needed because dependencies (like `requests`) aren't on TestPyPI.

## Publishing to PyPI

### Using API Token (Recommended)

1. Generate an API token at [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
2. Upload using the token:

```bash
twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: `pypi-AgEIcH...` (your API token)

### Using .pypirc Configuration

Create `~/.pypirc` for convenience:

```ini
[pypi]
username = __token__
password = pypi-AgEIcHlw...

[testpypi]
username = __token__
password = pypi-AgENdGVz...
```

**Important**: Set file permissions to restrict access:
```bash
chmod 600 ~/.pypirc
```

## Version Management

Update version in two places:

1. **pyproject.toml**:
```toml
[project]
version = "1.0.1"
```

2. **logdot/__init__.py**:
```python
__version__ = "1.0.1"
```

### Semantic Versioning

- **Patch** (1.0.0 -> 1.0.1): Bug fixes
- **Minor** (1.0.0 -> 1.1.0): New features, backwards compatible
- **Major** (1.0.0 -> 2.0.0): Breaking changes

## Clean Build

Always clean before building a new version:

```bash
rm -rf dist/ build/ *.egg-info/
python -m build
```

## Local Testing Before Upload

Test installation from the built wheel:

```bash
pip install dist/logdot_io_sdk-1.0.0-py3-none-any.whl
python -c "from logdot import LogDotLogger; print('Success!')"
pip uninstall logdot-io-sdk
```

## CI/CD Publishing (Optional)

For automated publishing via GitHub Actions:

1. Generate a PyPI API token
2. Add it as a GitHub secret named `PYPI_API_TOKEN`
3. Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI
on:
  release:
    types: [created]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## Troubleshooting

### "The user 'xxx' isn't allowed to upload to project 'logdot-io-sdk'"
The package name is already taken or you don't have permissions. Verify you own the package on PyPI.

### "File already exists"
You cannot overwrite an existing version. Bump the version number.

### "Invalid distribution file"
Run `twine check dist/*` to see detailed errors.

### "HTTPError: 400 Bad Request"
Check that all required metadata fields are present in `pyproject.toml`.

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [PEP 517 - Build System](https://peps.python.org/pep-0517/)
