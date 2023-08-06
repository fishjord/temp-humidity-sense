import adafruit_tca9548a
import adafruit_sht31d
import board
import time

from absl import app
from absl import flags
from absl import logging
from dataclasses import dataclass
from dataclass_csv import DataclassWriter
from datetime import datetime

FLAGS = flags.FLAGS

_OUTPUT_CSV = flags.DEFINE_string(
    'output_path', '/tmp/sense.csv',
    'Path to write sensor data to in csv format')
_SENSE_DELAY_SECONDS = flags.DEFINE_integer(
    'sense_delay_seconds', 60 * 5, 'Time between polling the sensors')
_HEAT_FOR_SECONDS = flags.DEFINE_integer(
    'heat_for_seconds', 0,
    'Amount of time to run the heater in each sensor after polling sensors. Total delay between sensor polling is equal to --heat_for_seconds + sense_delay_seconds'
)


@dataclass
class SensorData:
    '''Class for recording sensor readings'''

    timestamp: datetime
    channel_id: int
    temperature_celsius: float
    relative_humidity: float


def Sense() -> list[SensorData]:
    sense_time = datetime.now()
    sensor_data = []
    logging.info(f'Scan started at {sense_time}')
    with board.I2C() as i2c:
        tca = adafruit_tca9548a.TCA9548A(i2c)
        for channel in range(len(tca)):
            try:
                sensor = adafruit_sht31d.SHT31D(tca[channel])
                data = SensorData(timestamp=sense_time,
                                  channel_id=channel,
                                  temperature_celsius=sensor.temperature,
                                  relative_humidity=sensor.relative_humidity)

                logging.info(
                    f'Found sensor on channel {channel} with values {data}')
                sensor_data.append(data)
            except ValueError:
                logging.info(f'No sensor found on channel {channel}')

    return sensor_data


def HeatSensors(heat_for_seconds: float):
    logging.info(f'Heating started at {datetime.now()}')
    with board.I2C() as i2c:
        tca = adafruit_tca9548a.TCA9548A(i2c)
        for channel in range(len(tca)):
            try:
                sensor = adafruit_sht31d.SHT31D(tca[channel])
                sensor.heater = True
                logging.info(
                    f'Turning heater on for sensor on channel {channel}.')
            except ValueError:
                logging.info(f'No sensor found on channel {channel}')

        time.sleep(heat_for_seconds)

        for channel in range(len(tca)):
            try:
                sensor = adafruit_sht31d.SHT31D(tca[channel])
                sensor.heater = False
                logging.info(
                    f'Turning heater off for sensor on channel {channel}.')
            except ValueError:
                logging.info(f'No sensor found on channel {channel}')

    logging.info(f'Heating ended at {datetime.now()}')


def main(argv):
    del argv

    with open(_OUTPUT_CSV.value, 'a') as output_file:
        while True:
            sensor_data = Sense()
            sensor_writer = DataclassWriter(output_file, sensor_data,
                                            SensorData)
            sensor_writer.write(skip_header=True)
            if _HEAT_FOR_SECONDS.value > 0:
                HeatSensors(_HEAT_FOR_SECONDS.value)
            logging.info(
                f'Scan complete, sleeping for {_SENSE_DELAY_SECONDS.value} seconds'
            )
            time.sleep(_SENSE_DELAY_SECONDS.value)


if __name__ == '__main__':
    app.run(main)
