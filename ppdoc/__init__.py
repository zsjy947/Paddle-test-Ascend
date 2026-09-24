"""ppdoc —— 昇腾 NPU 上的文档解析核心库。

三条解析管线统一入口（通过 create_pipeline 按引擎名创建）：
- vl-server: PaddleOCRVL（PP-DocLayoutV2 版面本地推理 + vLLM 服务文字识别）
- structure: PPStructureV3（全本地推理，含印章识别）
- seal:      SealRecognition（印章独立识别）

命令行入口：python -m ppdoc parse|ocr|check
"""

from ppdoc.config import Settings
from ppdoc.pipelines import ENGINES, create_pipeline

__version__ = "0.1.0"

__all__ = ["Settings", "ENGINES", "create_pipeline", "__version__"]
