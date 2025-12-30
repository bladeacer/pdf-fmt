from typing import Dict, Any

from pdf_fmt.startup import setup_cli

def execute_main_pipeline(CONFIG: Dict[str, Any]) -> None:
    """
    Executes the main pipeline: CLI setup, dependency imports, config loading, 
    filter compilation, conversion, extraction, cleanup, and post-actions.
    """
    args = setup_cli()
    prints(args)
