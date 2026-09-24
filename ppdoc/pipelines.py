"""三条解析管线的工厂：vl-server / structure / seal。

构造参数默认值与历史脚本（test_ppdoclayout / test_ppstructure / test_seal_recognition）
逐字一致，行为不变。paddleocr 在函数内懒加载，宿主机（无 NPU）也能执行 --help、check。
"""

import os

from ppdoc.config import Settings

ENGINES = ("vl-server", "structure", "seal")

# PPStructureV3 版面检测自定义标签：保留 seal 类别（test_ppstructure.py 验证过的配置）
_STRUCTURE_LABEL_LIST = ["text", "title", "figure", "table", "seal", "footer", "header"]


def create_pipeline(engine: str, settings: Settings):
    """按引擎名创建解析管线。"""
    if engine == "vl-server":
        from paddleocr import PaddleOCRVL

        return PaddleOCRVL(
            vl_rec_backend="vllm-server",
            vl_rec_server_url=settings.vllm_server_url,
            vl_rec_api_model_name=settings.vllm_model_name,
            layout_detection_model_name="PP-DocLayoutV2",
            layout_detection_model_dir=settings.doclayout_model_dir,
            device=settings.device,
        )

    if engine == "structure":
        from paddleocr import PPStructureV3

        return PPStructureV3(
            use_doc_layout=True,
            use_seal_recognition=True,
            layout_config={
                "model_dir": settings.doclayout_model_dir,
                "label_list": _STRUCTURE_LABEL_LIST,
            },
            seal_config={
                "det_model_dir": settings.seal_det_model_dir,
                "rec_model_dir": settings.seal_rec_model_dir,
            },
            use_table_recognition=False,
            use_formula_recognition=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            device=settings.device,
        )

    if engine == "seal":
        from paddleocr import SealRecognition

        # 模型目录存在则用本地路径，否则回退库内置默认模型
        seal_config = {}
        if os.path.isdir(settings.seal_det_model_dir):
            seal_config["det_model_dir"] = settings.seal_det_model_dir
        if os.path.isdir(settings.seal_rec_model_dir):
            seal_config["rec_model_dir"] = settings.seal_rec_model_dir
        return SealRecognition(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            device=settings.device,
            **seal_config,
        )

    raise ValueError(f"未知引擎: {engine}（可选: {', '.join(ENGINES)}）")
