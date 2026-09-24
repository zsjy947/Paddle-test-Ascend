"""批量处理：异常隔离 + 失败重试 + 进度与耗时统计 + 汇总报告。"""

import glob
import json
import os
import time
from dataclasses import asdict, dataclass, field

from ppdoc import pipelines, postprocess


def collect_pdfs(input_dir: str) -> list:
    return sorted(glob.glob(os.path.join(input_dir, "*.pdf")))


@dataclass
class FileResult:
    name: str
    ok: bool
    elapsed: float = 0.0
    attempts: int = 0
    outputs: list = field(default_factory=list)
    error: str = ""


@dataclass
class BatchReport:
    engine: str
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    total_elapsed: float = 0.0
    files: list = field(default_factory=list)


def process_one(pipeline, input_path: str, output_dir: str, *, engine: str,
                restructure: bool = True, retries: int = 2, retry_backoff: float = 5.0) -> FileResult:
    """单文件处理：失败按线性退避重试，最终失败返回带错误信息的结果（不抛异常）。"""
    result = FileResult(name=os.path.basename(input_path), ok=False)
    attempts = retries + 1
    for attempt in range(1, attempts + 1):
        result.attempts = attempt
        start = time.perf_counter()
        try:
            result.outputs = postprocess.parse_and_save(
                pipeline, input_path, output_dir, engine=engine, restructure=restructure
            )
            result.elapsed = time.perf_counter() - start
            result.ok = True
            return result
        except Exception as e:  # 单文件失败不允许中断整批
            result.elapsed = time.perf_counter() - start
            result.error = f"{type(e).__name__}: {e}"
            if attempt < attempts:
                time.sleep(retry_backoff * attempt)
    return result


def run_batch(engine: str, input_paths: list, output_dir: str, settings, *,
              restructure: bool = True, retries: int = 2, retry_backoff: float = 5.0,
              log=print) -> BatchReport:
    """批量处理目录下全部文件，返回汇总报告。"""
    report = BatchReport(engine=engine, total=len(input_paths))
    pipeline = pipelines.create_pipeline(engine, settings)

    started = time.perf_counter()
    for idx, path in enumerate(input_paths, 1):
        result = process_one(
            pipeline, path, output_dir, engine=engine,
            restructure=restructure, retries=retries, retry_backoff=retry_backoff,
        )
        report.files.append(result)
        if result.ok:
            report.succeeded += 1
            if engine == "seal":
                dest = output_dir
            else:
                dest = os.path.relpath(result.outputs[0], output_dir) if result.outputs else ""
            log(f"[{idx}/{report.total}] OK   {result.name} ({result.elapsed:.1f}s) -> {dest}")
        else:
            report.failed += 1
            log(f"[{idx}/{report.total}] FAIL {result.name} (重试 {retries} 次后仍失败) {result.error}")
    report.total_elapsed = time.perf_counter() - started
    return report


def save_report(report: BatchReport, output_dir: str) -> str:
    """汇总报告落盘：output/batch_report.json。"""
    path = os.path.join(output_dir, "batch_report.json")
    payload = {
        "engine": report.engine,
        "total": report.total,
        "succeeded": report.succeeded,
        "failed": report.failed,
        "total_elapsed": report.total_elapsed,
        "files": [asdict(f) for f in report.files],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def print_summary(report: BatchReport, log=print):
    log("")
    log("=" * 60)
    log(f"批量处理完成: 共 {report.total}，成功 {report.succeeded}，"
        f"失败 {report.failed}，总耗时 {report.total_elapsed:.1f}s")
    for f in report.files:
        if not f.ok:
            log(f"  失败: {f.name} -> {f.error}")
    log("=" * 60)
