"""集中配置：全部环境变量的唯一读取点。

变量名与默认值与历史脚本保持一致，服务器侧既有用法不受影响。
"""

import os
from dataclasses import dataclass, field


def _env(key: str, default: str) -> str:
    value = os.environ.get(key)
    return value if value else default


@dataclass
class Settings:
    # ---- 模型路径（宿主机 /data1/models 挂载到 /app/models）----
    doclayout_model_dir: str = field(
        default_factory=lambda: _env("PPDOCLAYOUT_MODEL_PATH", "/app/models/PaddlePaddle/PP-DocLayoutV2")
    )
    seal_det_model_dir: str = field(
        default_factory=lambda: _env("SEAL_DET_MODEL_PATH", "/app/models/PaddlePaddle/PP-OCRv4_server_seal_det")
    )
    seal_rec_model_dir: str = field(
        default_factory=lambda: _env("SEAL_REC_MODEL_PATH", "/app/models/PaddlePaddle/PP-OCRv4_server_rec")
    )

    # ---- vLLM 服务 ----
    vllm_server_url: str = field(
        default_factory=lambda: _env("VLLM_SERVER_URL", "http://localhost:8000/v1")
    )
    vllm_model_name: str = field(
        default_factory=lambda: _env("VLLM_MODEL_NAME", "PaddleOCR-VL-0.9B")
    )

    # ---- 输入输出 ----
    output_dir: str = field(default_factory=lambda: _env("OUTPUT_DIR", "/app/paddle/output"))
    input_pdf_dir: str = field(default_factory=lambda: _env("INPUT_PDF_DIR", "/app/paddle/input/pdfs"))

    # ---- 运行设备 ----
    device: str = field(default_factory=lambda: _env("PPDOC_DEVICE", "npu"))

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
