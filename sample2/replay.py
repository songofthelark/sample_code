import argparse
import os
import gzip
from datetime import datetime
import json
from event_obj import Event
import sys
import re


def search(events: list, search_date: datetime, attribute: str):
    if not events:
        return None

    # yeah recursive binary search!
    if len(events) == 1:
        return events[0].get_attribute_observation(attribute)

    midpoint = round((len(events) - 1) / 2)
    midpoint_dt = events[midpoint].get_datetime()

    # NOTE what if we have two events with the same DT or within same second?
    # I don't think this works in that case
    if midpoint_dt == search_date:
        return events[midpoint].get_attribute_observation(attribute)

    high = len(events)
    low = 0
    if search_date < midpoint_dt:
        high = midpoint + 1
    else:
        low = midpoint + 1

    return search(events[low: high], search_date, attribute)


def run_search(events: list, search_date: datetime, attribute: str):
    target_value = search(events, search_date, attribute)

    if not target_value:
        print(f"Attribute {attribute} not found for date {search_date.isoformat()}")
        return None

    print(f"""
        Searched: {search_date.isoformat()}
        Attribute: {attribute}
        Value: {target_value.value}
        Last observed at: {target_value.obsdate}
        """)

    return target_value


def log_to_events(lines: list) -> list:
    events = []
    for n, line in enumerate(lines):
        try:
            event_dict = json.loads(line)
            event_dt = datetime.fromisoformat(event_dict["updateTime"])
            event = Event(event_dt, event_dict["update"])
            events.append(event)

            # if there was a previous event, add its values to the current event
            # but don't overwrite any
            if n > 0:
                event.set_attributes_from_event(events[n - 1])

        except json.JSONDecodeError:
            print(f"File line {n} not valid json")
            continue
        except KeyError as e:
            print(f"{e} not found in event")
            continue

    return events


def read_log(event_file_dir: str) -> list:
    event_file_open = open
    mode = 'r'
    if event_file_dir.lower().endswith(".gz"):
        event_file_open = gzip.open
        mode = 'rt'

    lines = []
    try:
        for event_file in os.listdir(event_file_dir):
            with event_file_open(event_file, mode) as f:
                for line in f:
                    lines.append(line)

    except gzip.BadGzipFile:
        print(f"File {event_file_dir} is not a valid gzip file")
        sys.exit(1)

    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='directory name', required=True)
    parser.add_argument('-d', help='date of event, ISO format, no timezone', required=True)
    parser.add_argument('-a', help='event attribute, case sensitive', required=True)
    args = parser.parse_args()

    # check if valid date
    try:
        search_date = datetime.fromisoformat(args.d).replace(tzinfo=None)  # in case someone put a TZ in there
    except ValueError:
        print(f"Date {args.d} is not a valid ISO date, must be in the format YYYY-MM-DDTHH:mm:ss")
        return

    # dirname yyyy/mm/dd.json(.gz)
    '''
    if not os.path.exists(args.f):
        print(f"File {args.f} not found")
        return
    '''

    # 2023-01-24T12:30:30
    m = re.search(r"(\d\d\d\d)-(\d\d)-(\d\d)", search_date)
    year = m.group(1)
    month = m.group(2)
    day = m.group(3)

    path = f"{args.f}/{year}/{month}/"
    if not os.path.isdir(path):
        print("it is not there")
        return

    log_lines = read_log(path)
    if not log_lines:
        print("No events in file")
        return

    events = log_to_events(log_lines)

    run_search(events, search_date, args.a)


if __name__ == "__main__":
    main()
