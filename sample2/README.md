# Erin Tavano --- Coding Sample

Here is my coding sample for parsing the thermostat log data.

Please feel free to contact me at emtavano@gmail.com

### To run

```
usage: replay.py [-h] -f /path/to/filename.jsonl -d 2016-07-17T02:31:00  -a attributeName

options:
  -h, --help  show this help message and exit
  -f filename        data file name, json lines format, may be gzipped
  -d date            date of event, ISO format, no timezone
  -a attribute       event attribute, case sensitive
  
```

### Example usage and output

```
python replay.py -f thermostat-data.jsonl -d 2016-03-06T06:43:30 -a coolTemp
```

**Output**
```
        Searched: 2016-03-06T06:43:30
        Attribute: coolTemp
        Value: 83
        Last observed at: 2016-03-03 06:42:00.004449
```

### Tests

Tests can be executed with pytest
```
pytest tests.py
```

****
