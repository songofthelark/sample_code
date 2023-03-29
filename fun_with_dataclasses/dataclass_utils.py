import csv
from collections import namedtuple
from typing import List, Type, Dict, Union
from dataclasses import dataclass
from enum import Enum
import re

TableMapping = namedtuple("TableMapping", ['table_name', 'format', 'bucket', 'prefix'])
FileType = Enum("FileType", ['PARQUET', "JSON"])


# frozen=True makes it immutable and therefore hashable
@dataclass(frozen=True)
class Column:
    name: str
    col_type: str
    dest_name: str


@dataclass(frozen=True)
class ParquetColumn(Column):
    converted_type: str
    compression: str


@dataclass(frozen=True)
class FileInfo:
    key: str
    columns: List[Column]
    table_name: str
    file_type: FileType


@dataclass(frozen=True)
class ParquetFileInfo(FileInfo):
    num_cols: str
    num_rows: str
    num_row_groups: str
    format_version: str


def csv_to_jsonl(filename: str) -> List[dict]:
    lines = []
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for row in reader:
            lines.append(row)

    return lines


def tablemapping_from_json(lines: Union[Dict, List[Dict]], nt: Type) -> Union[List, Dict]:
    mapping_list = []

    if type(lines) == dict:
        lines = [lines]

    for line in lines:
        obj = nt(**line)
        mapping_list.append(obj)

    #  if len(mapping_list) == 1:
    #     return mapping_list[0]

    return mapping_list


def fileinfo_from_json(lines: Union[Dict, List[Dict]]) -> Union[FileInfo, List]:
    if type(lines) == dict:
        lines = [lines]

    file_infos = []

    for line in lines:
        file_type = FileType.JSON
        if "file_type" in line and line["file_type"].upper() == "PARQUET":
            file_type = FileType.PARQUET

        # HACK right now the "key" field in that line
        # will have the filename in it, but we want the folder above it.
        # But there's no way to be sure that's a filename and not a folder without checking
        # just assume it is for now
        file_key = line["key"]
        if not file_key.endswith("/"):
            pos = file_key.rfind("/")
            line["key"] = file_key[:pos]

        columns = []
        for col_dict in line["columns"]:
            col_dict["dest_name"] = re.sub(r"\W", "_", col_dict["name"])
            # there's a better way to do this...
            if file_type == FileType.PARQUET:
                c = ParquetColumn(**col_dict)
            else:
                c = Column(**col_dict)
            columns.append(c)

        line["columns"] = columns
        line["file_type"] = file_type

        if file_type == FileType.PARQUET:
            fi = ParquetFileInfo(**line)
        else:
            fi = FileInfo(**line)

        file_infos.append(fi)

    if len(file_infos) == 1:
        return file_infos[0]

    return file_infos

