import multiprocessing
from typing import List

from .pages import PageProcessArgs, _process_page_text_block


def _run_processing_pool(args_list: List[PageProcessArgs], cores: int) -> List[str]:
    """Processes pages in parallel when possible and falls back to sequential."""
    if len(args_list) > 1 and cores > 1:
        try:
            with multiprocessing.Pool(processes=cores) as pool:
                return [
                    line
                    for page_result in pool.map(_process_page_text_block, args_list)
                    for line in page_result
                ]
        except Exception as e:
            print(f"Warning: Multiprocessing failed ({e}). Falling back to sequential.")

    return [
        line for args in args_list for line in _process_page_text_block(args)
    ]
