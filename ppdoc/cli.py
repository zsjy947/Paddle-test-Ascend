"""命令行入口：parse / ocr / check。

用法（容器内）:
    python -m ppdoc parse input/pdfs                     # 批量解析目录（默认 vl-server 引擎）
    python -m ppdoc parse a.pdf --engine structure       # 单文件，全本地管线
    python -m ppdoc parse --wait-vllm 600                # 等 vLLM 加载完成再批量
    python -m ppdoc ocr demo.png --task table            # 直连 vLLM API 识别单图
    python -m ppdoc check                                # 模型目录 + vLLM 就绪检查
"""

import argparse
import os

from ppdoc import pipelines
from ppdoc.batch import collect_pdfs, process_one, print_summary, run_batch, save_report
from ppdoc.client import TASKS, VLMOcrClient, check_vllm, wait_vllm
from ppdoc.config import Settings
from ppdoc.pipelines import ENGINES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ppdoc",
        description="昇腾 NPU 文档解析工具（PaddleOCR-VL / PP-DocLayoutV2 / PPStructureV3 / 印章识别）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="解析单个文件或整个目录（目录=批量）")
    p_parse.add_argument("input", nargs="?", default=None,
                         help="输入文件或目录；缺省取环境变量 INPUT_PDF_DIR")
    p_parse.add_argument("--engine", choices=ENGINES, default="vl-server",
                         help="解析引擎（默认 vl-server）")
    p_parse.add_argument("--output", default=None, help="输出目录（默认环境变量 OUTPUT_DIR）")
    p_parse.add_argument("--no-restructure", action="store_true",
                         help="跳过跨页表格合并/标题重建/多页拼接")
    p_parse.add_argument("--retries", type=int, default=2,
                         help="单文件失败重试次数（默认 2）")
    p_parse.add_argument("--wait-vllm", type=int, default=0, metavar="SEC",
                         help="vl-server 引擎下 vLLM 未就绪时最多等待秒数（默认 0 不等待）")

    p_ocr = sub.add_parser("ocr", help="直连 vLLM API 识别单张图片")
    p_ocr.add_argument("image", help="图片本地路径或 URL")
    p_ocr.add_argument("--task", choices=list(TASKS), default="ocr",
                       help="识别任务类型（默认 ocr）")

    sub.add_parser("check", help="检查模型目录与 vLLM 服务就绪状态")
    return parser


def _ensure_vllm(settings: Settings, wait_seconds: int) -> bool:
    ok, info = check_vllm(settings.vllm_server_url)
    if ok:
        return True
    if wait_seconds > 0:
        print(f"[INFO] vLLM 未就绪（{info}），最多等待 {wait_seconds}s ...")
        return wait_vllm(settings.vllm_server_url, timeout=wait_seconds)
    return False


def cmd_parse(settings: Settings, args) -> int:
    errors = settings.validate(args.engine)
    if errors:
        for e in errors:
            print(f"[ERROR] {e}")
        return 1

    if args.engine == "vl-server" and not _ensure_vllm(settings, args.wait_vllm):
        print(f"[ERROR] vLLM 服务未就绪: {settings.vllm_server_url}")
        print("请先启动: docker compose up -d vllm-ascend，或用 --wait-vllm 等待模型加载完成")
        return 1

    input_path = args.input or settings.input_pdf_dir
    if os.path.isdir(input_path):
        paths = collect_pdfs(input_path)
        if not paths:
            print(f"[INFO] {input_path} 中没有找到 PDF 文件")
            return 0
    elif os.path.isfile(input_path):
        paths = [input_path]
    else:
        print(f"[ERROR] 输入不存在: {input_path}")
        return 1

    output_dir = args.output or settings.output_dir
    os.makedirs(output_dir, exist_ok=True)
    do_restructure = not args.no_restructure

    print(f"引擎: {args.engine}")
    if args.engine == "vl-server":
        print(f"vLLM 地址: {settings.vllm_server_url}")
    print(f"输入: {input_path} ({len(paths)} 个文件)")
    print(f"输出目录: {output_dir}")
    print(f"跨页合并: {'开' if do_restructure else '关'}，失败重试: {args.retries} 次")
    print("-" * 50)

    if len(paths) == 1:
        pipeline = pipelines.create_pipeline(args.engine, settings)
        result = process_one(
            pipeline, paths[0], output_dir, engine=args.engine,
            restructure=do_restructure, retries=args.retries,
        )
        if result.ok:
            print(f"[OK] {result.name} ({result.elapsed:.1f}s)，已保存 {len(result.outputs)} 个文件")
            for p in result.outputs:
                print(f"  -> {p}")
            return 0
        print(f"[FAIL] {result.name} (重试 {args.retries} 次后仍失败) {result.error}")
        return 1

    report = run_batch(
        args.engine, paths, output_dir, settings,
        restructure=do_restructure, retries=args.retries,
    )
    print_summary(report)
    report_path = save_report(report, output_dir)
    print(f"汇总报告: {report_path}")
    return 0 if report.failed == 0 else 1


def cmd_ocr(settings: Settings, args) -> int:
    client = VLMOcrClient(settings.vllm_server_url, settings.vllm_model_name)
    text = client.recognize(args.image, task=args.task)
    print(f"Generated text: {text}")
    return 0


def cmd_check(settings: Settings) -> int:
    rc = 0
    print("== 配置来源 ==")
    print(f"配置文件: {settings.config_path or '未找到（环境变量 + 内置默认值）'}")
    print(f"设备: {settings.device}，版面模型名: {settings.layout_model_name}")
    print("== 模型目录 ==")
    for engine in ENGINES:
        dirs = settings.required_model_dirs(engine)
        if not dirs:
            optional = [
                ("印章检测模型(可选 SEAL_DET_MODEL_PATH)", settings.seal_det_model_dir),
                ("印章识别模型(可选 SEAL_REC_MODEL_PATH)", settings.seal_rec_model_dir),
            ]
            for name, path in optional:
                mark = "OK " if os.path.isdir(path) else "缺失（回退库内置默认模型）"
                print(f"[{engine}] {name}: {path} -> {mark}")
            continue
        for name, path in dirs.items():
            if os.path.isdir(path):
                print(f"[{engine}] {name}: {path} -> OK")
            else:
                print(f"[{engine}] {name}: {path} -> 缺失")
                rc = 1

    print("== vLLM 服务 ==")
    ok, info = check_vllm(settings.vllm_server_url)
    if ok:
        print(f"{settings.vllm_server_url} -> 就绪，已加载模型: {info}")
    else:
        print(f"{settings.vllm_server_url} -> 未就绪: {info}")
        rc = 1
    return rc


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.load()
    if args.command == "parse":
        return cmd_parse(settings, args)
    if args.command == "ocr":
        return cmd_ocr(settings, args)
    return cmd_check(settings)
