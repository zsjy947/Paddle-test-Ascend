"""集中配置：config.yaml + 环境变量双层覆盖，内置默认值兜底。

优先级：环境变量 > 配置文件 > 内置默认值。
- 配置文件路径：PPDOC_CONFIG 环境变量指定；缺省依次查找 仓库根/config.yaml、当前目录/config.yaml
- 环境变量名与历史版本保持一致（见 _ENV_OVERRIDES），服务器侧既有用法不受影响
"""

import os
import sys
from dataclasses import dataclass, field, fields

CONFIG_ENV = "PPDOC_CONFIG"

# 环境变量 → Settings 字段（变量名保持历史兼容）
_ENV_OVERRIDES = {
    "PPDOCLAYOUT_MODEL_PATH": "doclayout_model_dir",
    "PPDOCLAYOUT_MODEL_NAME": "layout_model_name",
    "SEAL_DET_MODEL_PATH": "seal_det_model_dir",
    "SEAL_REC_MODEL_PATH": "seal_rec_model_dir",
    "VLLM_SERVER_URL": "vllm_server_url",
    "VLLM_MODEL_NAME": "vllm_model_name",
    "OUTPUT_DIR": "output_dir",
    "INPUT_PDF_DIR": "input_pdf_dir",
    "PPDOC_DEVICE": "device",
}


@dataclass
class Settings:
    # ---- 运行设备 ----
    device: str = "npu"

    # ---- 模型（版本升级时改 config.yaml 即可，无需改代码）----
    # 版面模型名（vl-server 引擎传给 layout_detection_model_name）
    layout_model_name: str = "PP-DocLayoutV2"
    doclayout_model_dir: str = "/app/models/PaddlePaddle/PP-DocLayoutV2"
    seal_det_model_dir: str = "/app/models/PaddlePaddle/PP-OCRv4_server_seal_det"
    seal_rec_model_dir: str = "/app/models/PaddlePaddle/PP-OCRv4_server_rec"

    # ---- vLLM 服务 ----
    vllm_server_url: str = "http://localhost:8000/v1"
    # 需与 scripts/start_vllm.sh 的 VLLM_MODEL_NAME 保持一致
    vllm_model_name: str = "PaddleOCR-VL-0.9B"

    # ---- 输入输出 ----
    output_dir: str = "/app/paddle/output"
    input_pdf_dir: str = "/app/paddle/input/pdfs"

    # ---- 引擎构造参数（engines.<engine>.<参数>，见 config.yaml）----
    engines: dict = field(default_factory=dict)

    # 实际加载的配置文件路径（load() 填充，只读信息）
    config_path: str = ""

    def engine_config(self, engine: str) -> dict:
        """返回 engines.<engine> 段（缺省空 dict）。"""
        raw = (self.engines or {}).get(engine)
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            print(f"[WARN] 配置项 engines.{engine} 应为键值映射，已忽略", file=sys.stderr)
            return {}
        return dict(raw)

    def required_model_dirs(self, engine: str) -> dict:
        """返回引擎推理必需的 {说明(环境变量): 模型目录}。"""
        if engine == "vl-server":
            return {"版面分析模型(PPDOCLAYOUT_MODEL_PATH)": self.doclayout_model_dir}
        if engine == "structure":
            return {
                "版面分析模型(PPDOCLAYOUT_MODEL_PATH)": self.doclayout_model_dir,
                "印章检测模型(SEAL_DET_MODEL_PATH)": self.seal_det_model_dir,
                "印章识别模型(SEAL_REC_MODEL_PATH)": self.seal_rec_model_dir,
            }
        # seal 引擎：模型路径可选，未配置或不存在时回退库内置默认模型
        return {}

    def validate(self, engine: str) -> list:
        """校验引擎依赖的模型目录，返回错误信息列表（空列表 = 通过）。"""
        errors = []
        for name, path in self.required_model_dirs(engine).items():
            if not os.path.isdir(path):
                errors.append(f"{name} 目录不存在: {path}")
        return errors

    @classmethod
    def load(cls, config_path: str = None) -> "Settings":
        """加载配置：内置默认值 <- config.yaml <- 环境变量。"""
        data, path = _load_config_file(config_path)
        data = _apply_env_overrides(data)

        known = {f.name for f in fields(cls)} - {"config_path"}
        for key in list(data):
            if key not in known:
                print(f"[WARN] 配置项未知，已忽略: {key}", file=sys.stderr)
                del data[key]

        settings = cls(**data)
        settings.config_path = path or ""
        return settings


def _config_candidates(config_path=None) -> list:
    explicit = config_path or os.environ.get(CONFIG_ENV)
    if explicit:
        return [explicit]
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [os.path.join(repo_root, "config.yaml"), os.path.join(os.getcwd(), "config.yaml")]


def _load_config_file(config_path=None):
    """读取配置文件，返回 (配置 dict, 文件路径)；无可用文件时返回 ({}, None)。"""
    explicit = config_path or os.environ.get(CONFIG_ENV)
    path = next((p for p in _config_candidates(config_path) if os.path.isfile(p)), None)
    if path is None:
        if explicit:
            print(f"[ERROR] 配置文件不存在: {explicit}")
            sys.exit(1)
        return {}, None

    try:
        import yaml
    except ImportError:
        # 宿主机无 PyYAML 时降级为"仅环境变量 + 默认值"，容器内 paddleocr 自带 PyYAML
        print(f"[WARN] 未安装 PyYAML，忽略配置文件 {path}（pip install pyyaml 启用）", file=sys.stderr)
        return {}, None

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        print(f"[ERROR] 配置文件顶层应为键值映射: {path}")
        sys.exit(1)
    if not isinstance(data.get("engines", {}), dict):
        print(f"[ERROR] 配置项 engines 应为键值映射: {path}")
        sys.exit(1)
    return data, path


def _apply_env_overrides(data: dict) -> dict:
    data = dict(data)
    for env_name, field_name in _ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value:
            data[field_name] = value
    return data
