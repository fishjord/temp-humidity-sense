import adafruit_tca9548a
import adafruit_sht31d
import time

from absl import logging
from dataclasses import dataclass
from dataclass_csv import DataclassWriter
from datetime import datetime
from google.cloud import monitoring_v3
from google.protobuf.timestamp_pb2 import Timestamp
from typing import IO


@dataclass
class SensorData:
    '''Class for recording sensor readings'''

    timestamp: datetime
    device_id: str
    channel_id: int
    temperature_celsius: float
    relative_humidity: float


def Sense(sense_time: datetime, device_id: str, i2c) -> list[SensorData]:
    sensor_data = []
    logging.info(f'Scan started at {sense_time}')
    tca = adafruit_tca9548a.TCA9548A(i2c)
    for channel in range(len(tca)):
        try:
            sensor = adafruit_sht31d.SHT31D(tca[channel])
            data = SensorData(timestamp=sense_time,
                              device_id=device_id,
                              channel_id=channel,
                              temperature_celsius=sensor.temperature,
                              relative_humidity=sensor.relative_humidity)

            logging.info(
                f'Found sensor on channel {channel} with values {data}')
            sensor_data.append(data)
        except ValueError:
            logging.info(f'No sensor found on channel {channel}')

    return sensor_data


def HeatSensors(heat_for_seconds: float, i2c):
    logging.info(f'Heating started at {datetime.now()}')
    tca = adafruit_tca9548a.TCA9548A(i2c)
    for channel in range(len(tca)):
        try:
            sensor = adafruit_sht31d.SHT31D(tca[channel])
            sensor.heater = True
            logging.info(f'Turning heater on for sensor on channel {channel}.')
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


def WriteData(output: IO[str], data: list[SensorData]):
    sensor_writer = DataclassWriter(output, data, SensorData)
    sensor_writer.write(skip_header=True)


def _CreateTimeSeriesSkeleton(name: str,
                              data: SensorData) -> monitoring_v3.TimeSeries:
    time_series = monitoring_v3.TimeSeries()
    time_series.metric.type = f'custom.googleapis.com/environment/{name}'
    time_series.metric.labels['device_id'] = data.device_id
    time_series.metric.labels['channel_id'] = str(data.channel_id)
    time_series.resource.type = 'global'
    time_series.metric_kind = 'GAUGE'
    time_series.value_type = 'DOUBLE'

    point = monitoring_v3.Point()

    timestamp = Timestamp()
    timestamp.FromDatetime(data.timestamp)

    point.interval.end_time = timestamp

    time_series.points.append(point)

    return time_series


def _CreateForTemperature(data: SensorData) -> monitoring_v3.TimeSeries:
    time_series = _CreateTimeSeriesSkeleton('temperature', data)
    time_series.points[0].value.double_value = data.temperature_celsius
    return time_series


def _CreateForRelativeHumidity(data: SensorData) -> monitoring_v3.TimeSeries:
    time_series = _CreateTimeSeriesSkeleton('relative_humidity', data)
    time_series.points[0].value.double_value = data.relative_humidity
    return time_series


def SendDataToCloudMonitoring(client: monitoring_v3.MetricServiceClient,
                              project_id: str, data: list[SensorData]):
    request = monitoring_v3.CreateTimeSeriesRequest()
    request.name = f'projects/{project_id}'

    for d in data:
        request.time_series.append(_CreateForTemperature(d))
        request.time_series.append(_CreateForRelativeHumidity(d))

    response = client.create_time_series(request)
