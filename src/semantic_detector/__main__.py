"""模块入口点

允许通过 python -m semantic_detector 运行。
"""

import sys
from semantic_detector.cli import main

if __name__ == '__main__':
    sys.exit(main())
