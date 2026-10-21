"""Build the Windows installer and latest.json. Run build_exe.py first, then: python build_installer.py

The work lives in weatherlab/build_installer.py. This file runs it, so rebuild.bat and the release workflow use the same code.
"""

from weatherlab.build_installer import main

if __name__ == "__main__":
    raise SystemExit(main())
