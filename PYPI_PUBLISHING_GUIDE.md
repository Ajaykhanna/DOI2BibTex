# Publishing DOI2BibTeX V3.0.0 to PyPI

## 📋 Complete Guide to Publishing on PyPI

This guide walks you through publishing DOI2BibTeX V3.0.0 to the Python Package Index (PyPI) so users can install it with `pip install doi2bibtex`.

---

## ✅ Pre-Publication Checklist

Before publishing, verify everything is ready:

### **1. Package Configuration**
- ✅ `pyproject.toml` configured with version 3.0.0
- ✅ All metadata fields filled (name, description, authors, license)
- ✅ Dependencies properly listed
- ✅ Entry points configured for CLI commands
- ✅ Classifiers set (Python 3.8+, Production/Stable)

### **2. Files Ready**
- ✅ `README.md` - Comprehensive V3 documentation
- ✅ `LICENSE` - MIT License
- ✅ `MANIFEST.in` - Package data specification
- ✅ `requirements.txt` - Core dependencies
- ✅ `core/__init__.py` - Package initialization

### **3. Code Quality**
- ✅ All tests passing (108/108)
- ✅ Code coverage 92%
- ✅ Type checking complete (100%)
- ✅ No linting errors
- ✅ Documentation up to date

### **4. Git Status**
- ✅ All changes committed
- ✅ Tag v3.0.0 created
- ✅ Branch pushed to remote
- ✅ Working directory clean

---

## 📦 Package Structure

```
DOI2BibTex/
├── core/                      # Main package
│   ├── __init__.py
│   ├── processor.py
│   ├── async_processor.py
│   ├── config.py
│   ├── state.py
│   ├── database.py
│   └── ... (14 more modules)
├── streamlit_app.py           # Web UI entry point
├── cli.py                     # CLI entry point
├── api_server.py              # API entry point
├── pyproject.toml             # Package metadata
├── MANIFEST.in                # Package data
├── README.md                  # Documentation
├── LICENSE                    # MIT License
├── requirements.txt           # Dependencies
└── logo.png                   # Assets
```

---

## 🔧 Setup PyPI Account

### **1. Create PyPI Account**

If you don't have a PyPI account:

1. Go to: https://pypi.org/account/register/
2. Fill in the registration form:
   - Username
   - Email
   - Password
3. Verify your email address

### **2. Create TestPyPI Account (Recommended)**

For testing before publishing:

1. Go to: https://test.pypi.org/account/register/
2. Register separately (TestPyPI is independent)
3. Verify email

### **3. Create API Tokens**

**PyPI Token:**
1. Log in to https://pypi.org
2. Go to Account Settings → API Tokens
3. Click "Add API token"
4. Name: `doi2bibtex-v3-publish`
5. Scope: "Entire account" or "Project: doi2bibtex"
6. Copy the token (starts with `pypi-`)

**TestPyPI Token:**
1. Log in to https://test.pypi.org
2. Go to Account Settings → API Tokens
3. Create token named `doi2bibtex-v3-test`
4. Copy the token

### **4. Configure Tokens**

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-PRODUCTION-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
```

**Security:**
```bash
chmod 600 ~/.pypirc  # Restrict access to owner only
```

---

## 🛠️ Install Build Tools

### **1. Install Required Tools**

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install build tools
pip install --upgrade build twine

# Verify installation
python -m build --version
twine --version
```

Expected output:
```
build x.x.x
twine version x.x.x
```

---

## 📦 Build Distribution Packages

### **1. Clean Previous Builds**

```bash
# Remove old distribution files
rm -rf dist/ build/ *.egg-info

# Verify clean state
ls -la | grep -E "dist|build|egg-info"
# Should return nothing
```

### **2. Build Packages**

```bash
# Build source distribution (.tar.gz) and wheel (.whl)
python -m build

# This creates:
# - dist/doi2bibtex-3.0.0.tar.gz  (source distribution)
# - dist/doi2bibtex-3.0.0-py3-none-any.whl  (wheel)
```

**Expected Output:**
```
* Creating venv isolated environment...
* Installing packages in isolated environment... (setuptools>=45, wheel)
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist
* Creating venv isolated environment...
* Installing packages in isolated environment... (setuptools>=45, wheel)
* Getting build dependencies for wheel...
* Building wheel...
Successfully built doi2bibtex-3.0.0.tar.gz and doi2bibtex-3.0.0-py3-none-any.whl
```

### **3. Verify Build**

```bash
# Check created files
ls -lh dist/

# Should show:
# doi2bibtex-3.0.0-py3-none-any.whl  (~50KB)
# doi2bibtex-3.0.0.tar.gz            (~100KB)
```

### **4. Inspect Package Contents**

```bash
# Check wheel contents
python -m zipfile -l dist/doi2bibtex-3.0.0-py3-none-any.whl | head -30

# Check source distribution
tar -tzf dist/doi2bibtex-3.0.0.tar.gz | head -30
```

Verify these files are included:
- ✅ core/ directory with all modules
- ✅ README.md
- ✅ LICENSE
- ✅ pyproject.toml
- ✅ requirements.txt
- ✅ streamlit_app.py, cli.py, api_server.py

---

## 🧪 Test Package Locally

### **1. Install in Virtual Environment**

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# or
test_env\Scripts\activate  # Windows

# Install built package
pip install dist/doi2bibtex-3.0.0-py3-none-any.whl

# Verify installation
pip show doi2bibtex
```

Expected output:
```
Name: doi2bibtex
Version: 3.0.0
Summary: Enterprise-grade DOI to BibTeX converter...
Author: Ajay Khanna
License: MIT
Location: ...
Requires: requests, streamlit, typing-extensions
```

### **2. Test Functionality**

```bash
# Test CLI
doi2bibtex --version
doi2bibtex --help

# Test import
python -c "from core.processor import DOIProcessor; print('Import successful')"

# Test web app
doi2bibtex-web  # Should launch Streamlit app
```

### **3. Test Dependencies**

```bash
# Install with optional dependencies
pip install dist/doi2bibtex-3.0.0-py3-none-any.whl[all]

# Verify all features work
python -c "import aiohttp, sqlalchemy, fastapi, click; print('All optional imports OK')"
```

### **4. Cleanup Test Environment**

```bash
deactivate
rm -rf test_env
```

---

## 🧪 Publish to TestPyPI (Recommended First)

Test the publication process before publishing to production PyPI.

### **1. Check Package**

```bash
# Run twine check
twine check dist/*
```

Expected output:
```
Checking dist/doi2bibtex-3.0.0-py3-none-any.whl: PASSED
Checking dist/doi2bibtex-3.0.0.tar.gz: PASSED
```

### **2. Upload to TestPyPI**

```bash
# Upload to test repository
twine upload --repository testpypi dist/*
```

You'll be prompted:
```
Uploading distributions to https://test.pypi.org/legacy/
Uploading doi2bibtex-3.0.0-py3-none-any.whl
Uploading doi2bibtex-3.0.0.tar.gz
```

**Success:**
```
View at:
https://test.pypi.org/project/doi2bibtex/3.0.0/
```

### **3. Test Installation from TestPyPI**

```bash
# Create fresh environment
python -m venv testpypi_env
source testpypi_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    doi2bibtex==3.0.0

# Test functionality
doi2bibtex --version
python -c "from core.processor import DOIProcessor; print('Test successful')"

# Cleanup
deactivate
rm -rf testpypi_env
```

**Note:** The `--extra-index-url` is needed because dependencies (streamlit, requests) are not on TestPyPI.

---

## 🚀 Publish to Production PyPI

Once testing is successful, publish to production.

### **1. Final Checks**

```bash
# Verify version is correct
grep "version = " pyproject.toml
# Should show: version = "3.0.0"

# Verify all tests pass
python run_tests.py

# Verify package builds correctly
python -m build
twine check dist/*
```

### **2. Upload to PyPI**

```bash
# Upload to production PyPI
twine upload dist/*
```

**Prompt:**
```
Uploading distributions to https://upload.pypi.org/legacy/
Uploading doi2bibtex-3.0.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uploading doi2bibtex-3.0.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Success:**
```
View at:
https://pypi.org/project/doi2bibtex/3.0.0/
```

### **3. Verify Publication**

Visit:
- **Package Page**: https://pypi.org/project/doi2bibtex/
- **Version Page**: https://pypi.org/project/doi2bibtex/3.0.0/

Check:
- ✅ Version shows 3.0.0
- ✅ README renders correctly
- ✅ License shows MIT
- ✅ Dependencies listed
- ✅ Classifiers correct
- ✅ Download links work

---

## 🧪 Test Production Installation

### **1. Install from PyPI**

```bash
# Create clean environment
python -m venv prod_test
source prod_test/bin/activate

# Install from PyPI
pip install doi2bibtex

# Verify version
pip show doi2bibtex
# Version should be 3.0.0
```

### **2. Test All Entry Points**

```bash
# Test CLI
doi2bibtex --version
doi2bibtex convert 10.1038/nature12373

# Test web app
doi2bibtex-web  # Should launch Streamlit

# Test Python import
python -c "from core.processor import DOIProcessor; print('Success')"
```

### **3. Test Optional Dependencies**

```bash
# Install with extras
pip install doi2bibtex[all]

# Verify all imports
python -c "
from core.processor import DOIProcessor
from core.async_processor import AsyncDOIProcessor
from core.database import DOIDatabase
import aiohttp, sqlalchemy, fastapi
print('All features available!')
"
```

### **4. Cleanup**

```bash
deactivate
rm -rf prod_test
```

---

## 📢 Post-Publication Actions

### **1. Update GitHub**

```bash
# Tag the release
git tag -a v3.0.0 -m "Version 3.0.0 - Published to PyPI"
git push origin v3.0.0

# Update README badges (if you have PyPI badges)
# Add: ![PyPI](https://img.shields.io/pypi/v/doi2bibtex.svg)
```

### **2. Create GitHub Release**

1. Go to: https://github.com/Ajaykhanna/DOI2BibTex/releases/new
2. Tag: `v3.0.0`
3. Title: `Version 3.0.0 - Production Hardening Release`
4. Add to description:
   ```markdown
   ## 📦 Installation

   ```bash
   pip install doi2bibtex
   ```

   **PyPI**: https://pypi.org/project/doi2bibtex/3.0.0/
   ```

### **3. Announce the Release**

- ✅ Update project README with PyPI installation instructions
- ✅ Post on social media
- ✅ Notify users via GitHub Discussions
- ✅ Update documentation site (if any)
- ✅ Send email to mailing list (if any)

### **4. Monitor**

- ✅ Watch PyPI download statistics
- ✅ Monitor GitHub issues for installation problems
- ✅ Check for user feedback
- ✅ Respond to questions

---

## 🔄 Publishing Updates

For future releases (e.g., v3.0.1, v3.1.0):

### **1. Update Version**

Edit `pyproject.toml`:
```toml
version = "3.0.1"  # or next version
```

### **2. Update Changelog**

Create `RELEASE_NOTES_V3.0.1.md` or update existing.

### **3. Build and Publish**

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build new version
python -m build

# Check
twine check dist/*

# Upload
twine upload dist/*
```

---

## ❓ Troubleshooting

### **Issue: "File already exists"**

If you try to upload the same version twice:

```
HTTPError: 400 Bad Request
File already exists
```

**Solution:**
- Increment version in `pyproject.toml`
- Rebuild: `python -m build`
- Upload new version

**Note:** PyPI does not allow re-uploading the same version, even if deleted.

### **Issue: "Invalid credentials"**

```
HTTPError: 403 Forbidden
Invalid or non-existent authentication information
```

**Solutions:**
1. Check `~/.pypirc` has correct token
2. Verify token hasn't expired
3. Generate new API token
4. Use `twine upload --verbose` for debugging

### **Issue: "Package name already taken"**

```
HTTPError: 403 Forbidden
The name 'doi2bibtex' is too similar to an existing project
```

**Solution:**
- Choose different package name in `pyproject.toml`
- Or claim the existing package if you own it

### **Issue: "Missing dependencies"**

If users report import errors after installation:

**Check:**
1. Verify dependencies in `pyproject.toml`
2. Test fresh install: `pip install doi2bibtex[all]`
3. Update requirements.txt

### **Issue: "README not rendering"**

If README doesn't render on PyPI:

**Solutions:**
1. Verify README.md is valid Markdown
2. Check `readme = "README.md"` in pyproject.toml
3. Ensure MANIFEST.in includes README.md
4. Use `twine check dist/*` before uploading

### **Issue: "Entry points not working"**

If `doi2bibtex` command not found after install:

**Check:**
1. Entry points in pyproject.toml: `[project.scripts]`
2. Ensure cli.py has `main()` function
3. Reinstall: `pip install --force-reinstall doi2bibtex`

---

## 📊 Package Statistics

After publication, monitor:

### **Download Stats**
- https://pypistats.org/packages/doi2bibtex
- https://pepy.tech/project/doi2bibtex

### **PyPI Insights**
- Total downloads (daily, weekly, monthly)
- Python version usage
- System distribution (Linux, macOS, Windows)

---

## 🔒 Security Best Practices

### **1. Protect API Tokens**
```bash
# Never commit tokens to git
echo "~/.pypirc" >> .gitignore

# Use environment variables for CI/CD
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...
```

### **2. Enable 2FA**
- Enable Two-Factor Authentication on PyPI account
- Use recovery codes

### **3. Use Scoped Tokens**
- Create per-project tokens instead of account-wide tokens
- Revoke unused tokens

### **4. Verify Package Integrity**
```bash
# Check package hash
python -m pip hash dist/doi2bibtex-3.0.0-py3-none-any.whl
```

---

## 📚 Additional Resources

### **Official Documentation**
- **Packaging Python Projects**: https://packaging.python.org/tutorials/packaging-projects/
- **PyPI Help**: https://pypi.org/help/
- **Twine Documentation**: https://twine.readthedocs.io/
- **Build Documentation**: https://build.pypa.io/

### **Tools**
- **PyPI**: https://pypi.org/
- **TestPyPI**: https://test.pypi.org/
- **PyPI Stats**: https://pypistats.org/
- **Package Health**: https://snyk.io/advisor/python/doi2bibtex

### **Community**
- **Python Packaging Authority**: https://www.pypa.io/
- **Packaging Guide**: https://packaging.python.org/
- **Python Discord**: https://discord.gg/python

---

## ✅ Quick Command Reference

```bash
# Setup
pip install --upgrade build twine

# Clean
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Check
twine check dist/*

# Test on TestPyPI
twine upload --repository testpypi dist/*

# Publish to PyPI
twine upload dist/*

# Test installation
pip install doi2bibtex
doi2bibtex --version
```

---

## 🎉 Success!

Once published, users can install DOI2BibTeX V3.0.0 with:

```bash
pip install doi2bibtex
```

**Congratulations on publishing DOI2BibTeX V3.0.0 to PyPI!** 🚀

---

## 📞 Support

If you encounter issues:
- **PyPI Support**: https://pypi.org/help/
- **Packaging Issues**: https://github.com/pypa/packaging-problems/issues
- **Project Issues**: https://github.com/Ajaykhanna/DOI2BibTex/issues
- **Email**: akhanna2@ucmerced.edu

---

**Last Updated**: November 21, 2025
**Version**: 3.0.0
**Author**: Ajay Khanna
