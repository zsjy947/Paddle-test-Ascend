"""统一后处理：predict → restructure_pages → 保存。

文档管线（vl-server / structure）输出 output/<文件名>/<文件名>[_i].json + .md，
印章管线（seal）直接输出到 output/（json + 可视化图，无 markdown）。
"""

import os


def restructure_pages(pages_res, pipeline, merge_tables=True, relevel_titles=True, concatenate_pages=True):
    """跨页表格合并 + 多级标题重建 + 多页结果拼接。"""
    return pipeline.restructure_pages(
        pages_res,
        merge_tables=merge_tables,
        relevel_titles=relevel_titles,
        concatenate_pages=concatenate_pages,
    )


def save_doc_results(results, out_dir: str, basename: str) -> list:
    """保存文档管线结果：多结果时文件名加 _i 后缀（与历史输出结构一致）。"""
    saved = []
    for i, res in enumerate(results):
        suffix = f"_{i}" if len(results) > 1 else ""
        json_path = os.path.join(out_dir, f"{basename}{suffix}.json")
        md_path = os.path.join(out_dir, f"{basename}{suffix}.md")
        res.save_to_json(save_path=json_path)
        res.save_to_markdown(save_path=md_path)
        saved.extend([json_path, md_path])
    return saved


def save_seal_results(results, out_dir: str) -> list:
    """保存印章管线结果：save_to_img + save_to_json 直接落目录。"""
    for res in results:
        res.save_to_img(out_dir)
        res.save_to_json(out_dir)
    return [out_dir]


def parse_and_save(pipeline, input_path: str, output_dir: str, *, engine: str = "vl-server", restructure: bool = True) -> list:
    """单文件解析全流程，返回已保存文件列表。"""
    basename = os.path.splitext(os.path.basename(input_path))[0]

    if engine == "seal":
        os.makedirs(output_dir, exist_ok=True)
        results = list(pipeline.predict(input_path))
        return save_seal_results(results, output_dir)

    out_dir = os.path.join(output_dir, basename)
    os.makedirs(out_dir, exist_ok=True)
    pages = list(pipeline.predict(input_path))
    if restructure:
        pages = restructure_pages(pages, pipeline)
    return save_doc_results(pages, out_dir, basename)
