import multiprocessing
from typing import List

from .pages import PageProcessArgs, _process_page_text_block


def _run_processing_pool(args_list: List[PageProcessArgs], cores: int) -> List[str]:
    """Processes pages in parallel and falls back when a pool cannot start."""
    if len(args_list) > 1 and cores > 1:
        try:
            pool = multiprocessing.Pool(processes=cores)
        except (OSError, multiprocessing.ProcessError) as error:
            print(f"Warning: Multiprocessing unavailable ({error}). Falling back to sequential.")
        else:
            with pool:
                return [
                    line
                    for page_result in pool.map(_process_page_text_block, args_list)
                    for line in page_result
                ]

    return [
        line for args in args_list for line in _process_page_text_block(args)
    ]
