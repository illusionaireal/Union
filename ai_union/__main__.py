from .cli import main
import sys

# Machine-readable CLI JSON uses UTF-8 on Windows as on other platforms.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')

raise SystemExit(main())
