"""IPython magics for OpenDNA.

Usage in a notebook:

    %load_ext opendna_magic
    %opendna_url http://localhost:8765

    %%opendna fold
    MKTVRQERLKSIVRILER

    %opendna evaluate MKTVRQERLKSIVRILER
    %opendna analyze MKTVRQERLKSIVRILER
    %opendna fetch ubiquitin
"""
from __future__ import annotations

from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.display import JSON, display, HTML

from opendna.sdk import Client


@magics_class
class OpenDNAMagics(Magics):
    def __init__(self, shell=None):
        super().__init__(shell)
        self.client = Client("http://localhost:8765")

    @line_magic
    def opendna_url(self, url: str):
        """Set the OpenDNA API URL. Usage: %opendna_url http://host:port"""
        self.client = Client(url.strip())
        return f"OpenDNA client → {url.strip()}"

    @line_magic
    def opendna(self, line: str):
        """Line magic dispatch:
            %opendna evaluate <SEQ>
            %opendna fetch <name>
            %opendna analyze <SEQ>
        """
        parts = line.strip().split(None, 1)
        if not parts:
            return "usage: %opendna <verb> <arg>"
        verb, arg = parts[0], (parts[1] if len(parts) > 1 else "")
        if verb == "evaluate":
            return self.client.evaluate(arg)
        if verb == "analyze":
            return self.client.analyze(arg)
        if verb == "fetch":
            return self.client.fetch_uniprot(arg)
        return f"unknown verb: {verb}"

    @cell_magic
    def opendna_fold(self, line: str, cell: str):
        """Fold the cell contents (sequence) and display as JSON."""
        seq = cell.strip().replace("\n", "")
        result = self.client.fold(seq)
        return JSON(result if isinstance(result, dict) else {"result": str(result)})

    @cell_magic
    def opendna_analyze(self, line: str, cell: str):
        seq = cell.strip().replace("\n", "")
        return JSON(self.client.analyze(seq))

    @cell_magic
    def opendna_workflow(self, line: str, cell: str):
        """Run a JSON workflow graph defined in the cell."""
        import json
        wf = json.loads(cell)
        return JSON(self.client.run_workflow(wf))


def load_ipython_extension(ipython):
    ipython.register_magics(OpenDNAMagics)


def unload_ipython_extension(ipython):
    pass
