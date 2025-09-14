from dotenv import load_dotenv
from logging import getLogger as get_logger
from pydantic import BaseModel, Field, NonNegativeInt
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal, Any, TypeVar, TypeAlias, Type
import os
import json
import re
import pandas as pd
from IPython.display import Markdown, display, HTML

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.ai.documentintelligence.models import DocumentContentFormat
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentTable, DocumentTableCell

load_dotenv()

logger = get_logger(__name__)

this_dir = Path(__file__).parent
resources_dir = this_dir / "resources"
pdfdocs_dir = resources_dir / "pdfdocs"
temp_dir = this_dir / ".temp"
temp_dir.mkdir(exist_ok=True)



class DocExtractor(ABC):
    supported_extensions: list[Literal["pdf", "docx"]] = ["pdf", "docx"]

    def __init__(self, src: Path) -> None:
        self.source: Path = src
        self.doc_ext: Literal["pdf", "docx"]
        found_fileext: str = self.source.suffix.removeprefix(".").lower()
        if found_fileext in self.supported_extensions:
            self.doc_ext = found_fileext
        else:
            raise NotImplementedError
    
    @abstractmethod
    def extract(self): ...

    def __repr__(self) -> str:
        return f"DocExtr<{self.source.name}>"


class HTMLDocExtractor(DocExtractor):
    def extract(self):
        return
    
class MarkdownDocExtractor(DocExtractor):
    def extract(self):
        return

class AzureDocIntelMarkdownDocExtractor(DocExtractor):
    di_client_instance = None

    @classmethod
    def get_azuredocintel_client(cls) -> DocumentIntelligenceClient:
        # singleton method to return the same client always
        if cls.di_client_instance is None:
            di_key: str | None = os.environ.get("DI_KEY")
            di_endpoint: str | None = os.environ.get("DI_ENDPOINT")
            if (di_key is None) or (di_endpoint is None):
                raise ValueError
            cls.di_client_instance = DocumentIntelligenceClient(
                endpoint=di_endpoint, credential=AzureKeyCredential(di_key)
            )
        return cls.di_client_instance
    
    def analyse(self,) -> AnalyzeResult:
        docintelclient = self.get_azuredocintel_client()
        poller = docintelclient.begin_analyze_document(
            "prebuilt-layout", AnalyzeDocumentRequest(
                url_source=None,
                bytes_source=self.source.read_bytes()
            ),
            output_content_format=DocumentContentFormat.MARKDOWN
        )
        result: AnalyzeResult = poller.result()
        return result
    
    def extract(self):
        """extract the sections and pagenumber and other metadata"""
        return


class AzureDIDocTable:
    def __init__(
            self, 
            azdi_table: DocumentTable | None = None,
            html_source: str | None = None
        ) -> None:
        self.source: DocumentTable | None = azdi_table
        self.htmlsource: str | None = html_source
    
    @classmethod
    def from_html(cls, src: str) -> "AzureDIDocTable":
        return cls(html_source=src)
    
    def to_pandas(self) -> pd.DataFrame:
        if (self.source is None) and (self.htmlsource is None):
            raise ValueError
        if self.source:
            df = pd.DataFrame(self.source.cells)
            return df.pivot(columns=["columnIndex"], index=["rowIndex"], values=["content"]).reset_index(drop=True).T.reset_index(drop=True).T
        elif self.htmlsource:
            dfs: list[pd.DataFrame] = pd.read_html(self.htmlsource)
            assert len(dfs) == 1
            return dfs[0]
        else:
            raise NotImplementedError



class TagDetails(BaseModel):
    name: str
    content: str
    start_index: NonNegativeInt
    end_index: NonNegativeInt

    def __repr__(self) -> str:
        return f"[from_idx {self.start_index}]{self.content}[to_idx {self.end_index}]"

class CommentDetails(BaseModel):
    content: str
    start_index: NonNegativeInt
    end_index: NonNegativeInt

    def __repr__(self) -> str:
        return f"[from_idx {self.start_index}]{self.content}[to_idx {self.end_index}]"


class MarkdownContent:
    def __init__(self, source: str) -> None:
        self.content: str = source

    def identify_table_content(self) -> list[TagDetails]:
        return self._extract_tag_matches_with_indices(
            text = self.content,
            tag="table",
            include_tag=True,
        )
    
    def identify_comments(self) -> list[CommentDetails]:
        return self._fetch_comments(self.content)
    
    @staticmethod
    def _fetch_comments(text: str) -> list[CommentDetails]:
        pattern = r"<!--(.*?)-->"
        matches: list[CommentDetails] = []
        for m in re.finditer(pattern, text, re.DOTALL):
            content = m.group(0)
            start = m.start(0)
            end = m.end(0)

            comment_info = CommentDetails(
                content=content,
                start_index=start,
                end_index=end,
            )
            matches.append(comment_info)
        return matches

    @staticmethod
    def _extract_tag_matches_with_indices(
            text: str, 
            tag: str, 
            include_tag: bool = True
        ) -> list[TagDetails]:
        """
        Extracts either the full tag (with contents) or just the contents of the specified HTML/XML tag,
        along with their start and end indices in the input text.
        Does not handle nested tags.
        If include_tag is True, returns the full tag match; otherwise, returns only the contents.
        """
        if tag.lower() in ["hr", "img"]:
            # self closing tag pattern
            pattern = fr"<{tag}\b[^>]*\/?>"
        else:
            # general pattern for all xml and most of html tags
            pattern = fr"<{tag}[^>]*>(.*?)</{tag}>"
            

        matches: list[TagDetails] = []
        for m in re.finditer(pattern, text, re.DOTALL):
            if include_tag:
                content = m.group(0)
                start = m.start(0)
                end = m.end(0)
            else:
                content = m.group(1)
                start = m.start(1)
                end = m.end(1)
            tag_info = TagDetails(
                name=tag,
                content=content,
                start_index=start,
                end_index=end,
            )
            matches.append(tag_info)
        return matches


# source = pdfdocs_dir / "msword_multilevelnumbering.pdf"
source = pdfdocs_dir / "example.pdf"
extr = AzureDocIntelMarkdownDocExtractor(src=source)
extr.doc_ext
str(extr)
self = extr
self.source
result = self.analyse()


df = pd.DataFrame(result.paragraphs)
df

json_data = json.dumps(result.as_dict())
temp_file = (temp_dir / f"{source.name}.json")
temp_file.write_text(json_data, encoding='utf-8')

md_content = result.as_dict()["content"]
temp_file.with_suffix(".md").write_text(md_content, encoding="utf-8")

di_table = AzureDIDocTable(azdi_table=result.tables[0])
di_table.to_pandas()

table: DocumentTable = result.tables[0]
table.as_dict()
table




    
md = MarkdownContent(md_content)
tables_info: list[TagDetails] = md.identify_table_content()
for table in tables_info:
    doc_table = AzureDIDocTable.from_html(table.content)
    doc_table.to_pandas().to_markdown()

Markdown(doc_table.to_pandas().to_markdown())


md.identify_comments()

str(md)

# Example usage:
html = "santo<table id='santo'><tr><td>Cell</td></tr></table><table>santo</table>"
html = "santo<img id='santo' />"
md._extract_tag_matches_with_indices(html, "img")




# for idx, style in enumerate(result.styles):
#     print(
#         "Document contains {} content".format(
#          "handwritten" if style.is_handwritten else "no handwritten"
#         )
#     )

for page in result.pages:
    for line_idx, line in enumerate(page.lines):
        print(
         "...Line # {} has text content '{}'".format(
        line_idx,
        line.content.encode("utf-8")
        )
    )
    if page.selection_marks is None:
        print("No Page section marks found")
    else:
        for selection_mark in page.selection_marks:
            print(
            "...Selection mark is '{}' and has a confidence of {}".format(
            selection_mark.state,
            selection_mark.confidence
            )
        )

for table_idx, table in enumerate(result.tables):
    print(
        "Table # {} has {} rows and {} columns".format(
        table_idx, table.row_count, table.column_count
        )
    )
        
    for cell in table.cells:
        print(
            "...Cell[{}][{}] has content '{}'".format(
            cell.row_index,
            cell.column_index,
            cell.content.encode("utf-8"),
            )
        )



df = pd.DataFrame()
rows: list[list[Any]] = []
for cell in table.cells:
    row = []
    cell.column_index = cell.content
df

DocumentTable, DocumentTableCell



