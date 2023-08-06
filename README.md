# Temperature Humidity Continous Sensing Script

This script continously polls sht31-d sensors connected to a tca9548a
multiplexer and records the temperature and humidty readings to a csv file.

[CircuitPython](https://circuitpython.org/) must be installed to use this
script. The rest of the dependencies can be installed with pipenv.

Example usage:

Without pipenv
```bash
python3 sense_main.py --output_path=path/to/output.csv --sense_delay_seconds=300
```

With pipenv:
```bash
pipenv run sense_main.py --output_path=path/to/output.csv --sense_delay_seconds=300
```
