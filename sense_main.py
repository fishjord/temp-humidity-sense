import board
import time
import sense

from absl import app
from absl import flags
from absl import logging
from datetime import datetime

FLAGS = flags.FLAGS

_OUTPUT_CSV = flags.DEFINE_string(
    'output_path', '/tmp/sense.csv',
    'Path to write sensor data to in csv format')
_SENSE_DELAY_SECONDS = flags.DEFINE_integer(
    'sense_delay_seconds', 60 * 5, 'Time between polling the sensors')
_HEAT_FOR_SECONDS = flags.DEFINE_integer(
    'heat_for_seconds', 0,
    'Amount of time to run the heater in each sensor after polling sensors. '
    'Total delay between sensor polling is equal to --heat_for_seconds + '
    '--sense_delay_seconds')
_DEVICE_ID = flags.DEFINE_string('device_id', '', 'Unique id of this device')


def main(argv):
    del argv

    with open(_OUTPUT_CSV.value, 'a') as output_file:
        with board.I2C() as i2c:
            while True:
                sensor_data = sense.Sense(datetime.now(), _DEVICE_ID.value,
                                          i2c)
                sense.WriteData(output_file, sensor_data)

                if _HEAT_FOR_SECONDS.value > 0:
                    sense.HeatSensors(_HEAT_FOR_SECONDS.value, i2c)
                logging.info(
                    f'Scan complete, sleeping for {_SENSE_DELAY_SECONDS.value} '
                    'seconds')
                time.sleep(_SENSE_DELAY_SECONDS.value)


if __name__ == '__main__':
    app.run(main)
