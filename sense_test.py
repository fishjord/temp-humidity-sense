import adafruit_tca9548a
import adafruit_sht31d
import datetime
import patch
import sense
import unittest

from io import StringIO
from google.cloud import monitoring_v3
from google.protobuf import text_format
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch
from unittest.mock import PropertyMock


class SenseTest(unittest.TestCase):

    @patch('adafruit_tca9548a.TCA9548A')
    @patch('adafruit_sht31d.SHT31D')
    def test_sense_data(self, sht31d, tca9548a):
        i2c = Mock()
        tca = MagicMock()
        tca.__len__.return_value = 2
        tca9548a.return_value = tca

        sensor_mocks = [MagicMock(), MagicMock()]
        sht31d.side_effect = sensor_mocks

        type(sensor_mocks[0]).temperature = PropertyMock(return_value=0)
        type(sensor_mocks[0]).relative_humidity = PropertyMock(return_value=1)
        type(sensor_mocks[1]).temperature = PropertyMock(return_value=2)
        type(sensor_mocks[1]).relative_humidity = PropertyMock(return_value=3)

        expected_time = datetime.datetime(2023, 4, 2, 12, 56, 31)
        device_id = 'device_id'
        data = sense.Sense(expected_time, device_id, i2c)

        self.assertListEqual(data, [
            sense.SensorData(timestamp=expected_time,
                             device_id=device_id,
                             channel_id=0,
                             temperature_celsius=0,
                             relative_humidity=1),
            sense.SensorData(timestamp=expected_time,
                             device_id=device_id,
                             channel_id=1,
                             temperature_celsius=2,
                             relative_humidity=3),
        ])

    @patch('adafruit_tca9548a.TCA9548A')
    @patch('adafruit_sht31d.SHT31D')
    def test_heat_sensors(self, sht31d, tca9548a):
        i2c = Mock()
        tca = MagicMock()
        tca.__len__.return_value = 1
        tca9548a.return_value = tca

        sensors = [MagicMock(), MagicMock()]
        heaters = [PropertyMock(), PropertyMock()]
        type(sensors[0]).heater = heaters[0]
        type(sensors[1]).heater = heaters[1]
        sht31d.side_effect = sensors

        start = datetime.datetime.now()
        heat_time_seconds = 1
        sense.HeatSensors(heat_time_seconds, i2c)
        end = datetime.datetime.now()

        self.assertGreater(end - start,
                           datetime.timedelta(seconds=heat_time_seconds))
        heaters[0].assert_called_with(True)
        heaters[1].assert_called_with(False)

    def test_write_sensor_data(self):
        string_stream = StringIO()
        time = datetime.datetime(2023, 4, 2, 12, 56, 31)

        data = [
            sense.SensorData(timestamp=time,
                             device_id='device_1',
                             channel_id=0,
                             temperature_celsius=0,
                             relative_humidity=1),
            sense.SensorData(timestamp=time,
                             device_id='device_2',
                             channel_id=1,
                             temperature_celsius=2,
                             relative_humidity=3)
        ]

        sense.WriteData(string_stream, data)

        self.assertEqual(
            string_stream.getvalue(), '2023-04-02 12:56:31,device_1,0,0,1\r\n'
            '2023-04-02 12:56:31,device_2,1,2,3\r\n')

    def test_send_data_to_cloud_monitoring(self):
        time = datetime.datetime(2023, 4, 2, 12, 56, 31)
        data = [
            sense.SensorData(timestamp=time,
                             device_id='device_1',
                             channel_id=0,
                             temperature_celsius=0,
                             relative_humidity=1),
            sense.SensorData(timestamp=time,
                             device_id='device_2',
                             channel_id=1,
                             temperature_celsius=2,
                             relative_humidity=3)
        ]

        client = Mock()
        sense.SendDataToCloudMonitoring(client, 'my-project', data)

        expected_request = monitoring_v3.CreateTimeSeriesRequest()

        text_format.Parse(
            '''
name: "projects/my-project"
time_series {
  metric {
    type: "custom.googleapis.com/environment/temperature"
    labels {
      key: "device_id"
      value: "device_1"
    }
    labels {
      key: "channel_id"
      value: "0"
    }
  }
  resource {
    type: "global"
  }
  metric_kind: GAUGE
  value_type: DOUBLE
  points {
    interval {
      end_time {
        seconds: 1680440191
      }
    }
    value {
      double_value: 0
    }
  }
}
time_series {
  metric {
    type: "custom.googleapis.com/environment/relative_humidity"
    labels {
      key: "device_id"
      value: "device_1"
    }
    labels {
      key: "channel_id"
      value: "0"
    }
  }
  resource {
    type: "global"
  }
  metric_kind: GAUGE
  value_type: DOUBLE
  points {
    interval {
      end_time {
        seconds: 1680440191
      }
    }
    value {
      double_value: 1
    }
  }
}
time_series {
  metric {
    type: "custom.googleapis.com/environment/temperature"
    labels {
      key: "device_id"
      value: "device_2"
    }
    labels {
      key: "channel_id"
      value: "1"
    }
  }
  resource {
    type: "global"
  }
  metric_kind: GAUGE
  value_type: DOUBLE
  points {
    interval {
      end_time {
        seconds: 1680440191
      }
    }
    value {
      double_value: 2
    }
  }
}
time_series {
  metric {
    type: "custom.googleapis.com/environment/relative_humidity"
    labels {
      key: "device_id"
      value: "device_2"
    }
    labels {
      key: "channel_id"
      value: "1"
    }
  }
  resource {
    type: "global"
  }
  metric_kind: GAUGE
  value_type: DOUBLE
  points {
    interval {
      end_time {
        seconds: 1680440191
      }
    }
    value {
      double_value: 3
    }
  }
}''', expected_request._pb)
        client.create_time_series.assert_called_once_with(expected_request)


if __name__ == '__main__':
    unittest.main()
