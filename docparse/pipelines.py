"""三条解析管线的工厂：vl-server / structure / seal。

模型路径/名称、device 等关键参数由 Settings 顶层配置统一注入；
config.yaml 中 engines.<引擎> 段内未被消费的参数会原样透传给 paddleocr
对应构造器 —— paddleocr / 模型升级引入新参数时，改配置文件即可，无需改代码。
"""

import os
import sys

from docparse.config import Settings

ENGINES = ("vl-server", "structure", "seal")

# 各引擎中由顶层配置统一注入、不允许在引擎段重复出现的参数
_RESERVED = {
    "vl-server": {"vl_rec_server_url", "vl_rec_api_model_name",
                  "layout_detection_model_name", "layout_detection_model_dir", "device"},
    "structure": {"layout_config", "seal_config", "device"},
    "seal": {"det_model_dir", "rec_model_dir", "device"},
}

# 无配置文件时的行为兜底（与历史脚本逐字一致）
_STRUCTURE_DEFAULTS = {
    "use_doc_layout": True,
    "use_seal_recognition": True,
    "use_table_recognition": False,
    "use_formula_recognition": False,
    "use_doc_orientation_classify": False,
    "use_doc_unwarping": False,
}
_SEAL_DEFAULTS = {
    "use_doc_orientation_classify": False,
    "use_doc_unwarping": False,
}
_DEFAULT_LABEL_LIST = ["text", "title", "figure", "table", "seal", "footer", "header"]


def _passthrough(settings: Settings, engine: str) -> dict:
    """提取引擎段中可透传给 paddleocr 构造器的参数，保留参数出现时告警忽略。"""
    extra = {}
    for key, value in settings.engine_config(engine).items():
        if key in _RESERVED[engine]:
            print(f"[WARN] engines.{engine}.{key} 由顶层配置统一注入，已忽略", file=sys.stderr)
        else:
            extra[key] = value
    return extra


def build_pipeline_kwargs(engine: str, settings: Settings) -> dict:
    """组装引擎构造参数（不触发 paddleocr import，宿主机可检查/可测试）。"""
    if engine == "vl-server":
        cfg = settings.engine_config(engine)
        backend = cfg.get("vl_rec_backend", "vllm-server")
        kwargs = {
            "vl_rec_backend": backend,
            "vl_rec_server_url": settings.vllm_server_url,
            "vl_rec_api_model_name": settings.vllm_model_name,
            "layout_detection_model_name": settings.layout_model_name,
            "layout_detection_model_dir": settings.doclayout_model_dir,
            "device": settings.device,
        }
        kwargs.update(_passthrough(settings, engine))
        return kwargs

    if engine == "structure":
        label_list = settings.engine_config(engine).get("layout_label_list", _DEFAULT_LABEL_LIST)
        kwargs = {
            "layout_config": {
                "model_dir": settings.doclayout_model_dir,
                "label_list": label_list,
            },
            "seal_config": {
                "det_model_dir": settings.seal_det_model_dir,
                "rec_model_dir": settings.seal_rec_model_dir,
            },
            "device": settings.device,
        }
        kwargs.update(_STRUCTURE_DEFAULTS)       # 无配置时兜底
        kwargs.update(_passthrough(settings, engine))  # 配置覆盖 + 透传新参数
        return kwargs

    if engine == "seal":
        kwargs = {"device": settings.device}
        kwargs.update(_SEAL_DEFAULTS)
        kwargs.update(_passthrough(settings, engine))
        # 模型目录存在则用本地路径，否则回退库内置默认模型
        if os.path.isdir(settings.seal_det_model_dir):
            kwargs.setdefault("det_model_dir", settings.seal_det_model_dir)
        if os.path.isdir(settings.seal_rec_model_dir):
            kwargs.setdefault("rec_model_dir", settings.seal_rec_model_dir)
        return kwargs

    raise ValueError(f"未知引擎: {engine}（可选: {', '.join(ENGINES)}）")


def create_pipeline(engine: str, settings: Settings):
    """按引擎名创建解析管线。"""
    kwargs = build_pipeline_kwargs(engine, settings)

    if engine == "vl-server":
        from paddleocr import PaddleOCRVL

        return PaddleOCRVL(**kwargs)

    if engine == "structure":
        from paddleocr import PPStructureV3

        return PPStructureV3(**kwargs)

    if engine == "seal":
        from paddleocr import SealRecognition

        return SealRecognition(**kwargs)

    raise ValueError(f"未知引擎: {engine}（可选: {', '.join(ENGINES)}）")
