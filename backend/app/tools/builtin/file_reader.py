"""
文件读取工具
支持 CSV、Excel、PDF、TXT 等格式的智能解析
"""
import os
import json
from typing import Optional
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolResult


class FileReaderInput(BaseModel):
    file_path: str = Field(description="文件路径（相对于 data/ 目录或绝对路径）")
    file_type: Optional[str] = Field(
        default=None,
        description="文件类型: csv, excel, pdf, txt, json。不指定则自动推断"
    )
    max_rows: int = Field(default=50, description="最大读取行数")


class FileReaderTool(BaseTool):
    name = "file_reader"
    description = (
        "读取并解析本地文件系统中的文件。"
        "支持 CSV、Excel（.xlsx）、PDF、TXT 和 JSON 格式。"
        "输入：文件路径，可选的文件类型和最大行数。"
    )
    category = "file"

    DATA_DIR = "./data"

    async def _execute(
        self, file_path: str, file_type: str = None, max_rows: int = 50
    ) -> ToolResult:
        full_path = file_path
        if not os.path.isabs(file_path):
            full_path = os.path.join(self.DATA_DIR, file_path)

        if not os.path.exists(full_path):
            return ToolResult(
                success=False,
                data=None,
                error=f"File not found: {full_path}",
            )

        ext = file_type or os.path.splitext(full_path)[1].lower().lstrip(".")

        try:
            if ext in ("csv",):
                return await self._read_csv(full_path, max_rows)
            elif ext in ("xlsx", "xls", "excel"):
                return await self._read_excel(full_path, max_rows)
            elif ext in ("pdf",):
                return await self._read_pdf(full_path, max_rows)
            elif ext in ("json",):
                return await self._read_json(full_path, max_rows)
            elif ext in ("txt", "md", "log"):
                return await self._read_text(full_path, max_rows)
            else:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Unsupported file type: {ext}",
                )
        except ImportError as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"Missing dependency: {e}. Please install required packages.",
            )

    async def _read_csv(self, path: str, max_rows: int) -> ToolResult:
        import pandas as pd
        df = pd.read_csv(path).head(max_rows)
        return ToolResult(
            success=True,
            data=f"CSV File: {os.path.basename(path)}\n"
                 f"Shape: {df.shape}\n"
                 f"Columns: {list(df.columns)}\n\n"
                 f"{df.to_string()}",
        )

    async def _read_excel(self, path: str, max_rows: int) -> ToolResult:
        import pandas as pd
        xl = pd.ExcelFile(path)
        sheets_info = []
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet).head(max_rows)
            sheets_info.append(
                f"--- Sheet: {sheet} ---\n"
                f"Shape: {df.shape}\n"
                f"Columns: {list(df.columns)}\n\n"
                f"{df.to_string()}"
            )
        return ToolResult(
            success=True,
            data=f"Excel File: {os.path.basename(path)}\n\n" + "\n\n".join(sheets_info),
        )

    async def _read_pdf(self, path: str, max_rows: int) -> ToolResult:
        import PyPDF2
        reader = PyPDF2.PdfReader(path)
        pages_text = []
        for i, page in enumerate(reader.pages[:min(len(reader.pages), 3)]):
            text = page.extract_text()
            if text:
                pages_text.append(f"--- Page {i+1} ---\n{text[:2000]}")
        return ToolResult(
            success=True,
            data=f"PDF File: {os.path.basename(path)}\n"
                 f"Pages: {len(reader.pages)}\n\n" + "\n".join(pages_text),
        )

    async def _read_json(self, path: str, max_rows: int) -> ToolResult:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if len(text) > 3000:
            text = text[:3000] + "\n... (truncated)"
        return ToolResult(success=True, data=f"JSON File: {os.path.basename(path)}\n{text}")

    async def _read_text(self, path: str, max_rows: int) -> ToolResult:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:max_rows]
        return ToolResult(
            success=True,
            data=f"Text File: {os.path.basename(path)}\n" + "".join(lines),
        )

    def get_input_schema(self):
        return FileReaderInput
