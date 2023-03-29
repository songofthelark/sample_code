import boto3
import pyarrow.parquet as pq
import json
from parquet_tools.commands.utils import ParquetFile, to_parquet_file
from datetime import datetime
import dataclasses
from dataclass_utils import *
import os
import dateparser
from botocore.exceptions import ClientError
import sys


def list_files(bucket_name: str, prefix: str = None, extension: str = "") -> List:
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    bucket_filter = {}
    if prefix:
        bucket_filter = {"Prefix": prefix}

    object_summary_iterator = bucket.objects.filter(**bucket_filter)

    files = []
    for obj_sum in object_summary_iterator:
        if obj_sum.key.endswith(extension) and not obj_sum.key.endswith("/") and "old_format" not in obj_sum.key:
            files.append(obj_sum)

    return files


def get_parquet_schema(file_meta, schema) -> str:

    columns: List[str] = schema.names

    pqc_list = []
    for i, column in enumerate(columns):
        col = schema.column(i)
        col_meta = file_meta.row_group(0).column(i)
        col_compression = f"{col_meta.compression}"

        # if there's no logical type,  col.logical_type back as object with type "None", not None
        col_type = str(col.logical_type) if str(col.logical_type) != "None" else col.physical_type

        pqc = ParquetColumn(name=col.name, col_type=col_type, converted_type=col.converted_type,
                            compression=col_compression, dest_name=col.name)
        pqc_list.append(pqc)

    return pqc_list


def get_json_info(bucket_name: str, file_key: str, table_name: str, line_limit: int = 10000) -> FileInfo:

    temp_filename = 'temp'

    # i guess we read through the whole file?
    # could just guess from the first line
    s3 = boto3.client('s3')

    # file key contains the bucket name, gotta take it out
    file_prefix = file_key[len(bucket_name)+6:]
    fields = {}

    try:
        with open(temp_filename, 'wb') as f:
            s3.download_fileobj(bucket_name, file_prefix, f)
    except ClientError as e:
        print(f"Warning for {file_key}: {str(e)}")
        return None

    with open(temp_filename) as f:
        for n, line in enumerate(f, start=1):
            data = json.loads(line)
            for k, v in data.items():
                # guess type type of value
                if k not in fields:
                    fields[k] = set()

                if v is None:
                    # no idea what it is
                    continue

                # maybe it's a date? does it have date or time in the name?
                named_as_date = any([x in k.lower() for x in ['date', 'time']])

                if named_as_date and dateparser.parse(v):
                    col = Column(k, 'TIMESTAMP_TZ', k)
                    fields[k].add(col)
                    continue

                col = Column(k, type(v).__name__, k)
                fields[k].add(col)
                if len(fields[k]) > 1:
                    print(f"Warning, multiple types for {k}, starting at line {n}")

            if line_limit and n == line_limit:
                break

    os.remove(temp_filename)

    # no fields in the file for some reason
    if not fields:
        return None

    columns = []
    for col in fields.values():
        columns.extend(col)

    fileinfo = FileInfo(key=file_key, columns=columns, table_name=table_name, file_type=FileType.JSON)
    return fileinfo


def get_parquet_info(file_key: str, table_name: str) -> ParquetFileInfo:
    pf: ParquetFile = to_parquet_file(file_exp=file_key, awsprofile=None, endpoint_url=None)

    with pf.get_local_path() as local_path:
        pq_file: pq.ParquetFile = pq.ParquetFile(local_path)
        file_meta: pq.FileMetaData = pq_file.metadata

        file_schema: pq.ParquetSchema = pq_file.schema
        columns = get_parquet_schema(file_meta, file_schema)

        pqi = ParquetFileInfo(table_name=table_name, key=file_key, num_cols=file_meta.num_columns, num_rows=file_meta.num_rows,
                              num_row_groups=file_meta.num_row_groups, format_version=file_meta.format_version,
                              columns=columns, file_type=FileType.PARQUET)
        return pqi


def serialize_file_info(fi: FileInfo) -> dict:

    column: Column  # this gets rid of the warning for asdict, somehow
    dict_list = []
    for column in fi.columns:
        col_dict = dataclasses.asdict(column)
        dict_list.append(col_dict)

    fi_dict = dataclasses.asdict(fi)
    fi_dict["file_type"] = fi.file_type.name
    fi_dict["columns"] = dict_list

    return fi_dict


def datestring():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main(mapping_file=None):

    if not mapping_file:
        if len(sys.argv) != 2:
            print("Put a table mapping file name")
            return

        mapping_file = sys.argv[1]

    json_lines = csv_to_jsonl(mapping_file)
    mappings = tablemapping_from_json(json_lines, TableMapping)

    datestamp = datestring()
    mapping: TableMapping
    for mapping in mappings:

        extension = ""  # mapping.format
        # TODO change back to None for  raw data
        limit = 5
        if mapping.format == "json":
            extension = ""
            # just look at any N files, not all of them, because they're the output of some
            # job anyway.  There might be extra fields in there somewhere but just a couple
            # of files is good enough
            limit = 2

        file_list = list_files(mapping.bucket, mapping.prefix, extension=extension)

        with open(f"file_info_{mapping.table_name}_{datestamp}.jsonl", 'w') as f:
            for n, obj_sum in enumerate(file_list, start=1):
                file = f"s3://{mapping.bucket}/{obj_sum.key}"
                print(n, file)
                if mapping.format == "parquet":
                    fi = get_parquet_info(file, table_name=mapping.table_name)
                else:
                    # it's json
                    fi = get_json_info(mapping.bucket, file, table_name=mapping.table_name)

                if not fi:
                    continue

                serialized = serialize_file_info(fi)
                f.write(json.dumps(serialized) + "\n")

                if limit and n == limit:
                    break



if __name__ == "__main__":
    main("s3.tsv")
 