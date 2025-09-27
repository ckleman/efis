"""
efis_sensors.py

EFIS Sensor Backend Module (full-featured)
- BNO085 (IMU)
- MPRLS (Barometric pressure)
- 2x ADS1015 (Analog inputs)
Features:
- Initialization and safe fail handling
- Exponential Moving Average smoothing
- Unit conversions (m<->ft, hPa<->inHg)
- Fault detection with configurable behavior:
    fault_mode = "silent" | "warn" | "exception"
- Status reporting and timestamping
- Optional text-file logging of faults/warnings (timestamped)
"""

from __future__ import annotations
import time
import datetime
import logging
import board
import busio

# Adafruit drivers
import adafruit_bno08x
from adafruit_bno08x.i2c import BNO08X_I2C
import adafruit_mprls
from adafruit_ads1x15.ads1015 import ADS1015
from adafruit_ads1x15.analog_in import AnalogIn


class SensorFault(Exception):
    """Raised when a critical sensor fault occurs and fault_mode == 'exception'."""
    pass


class EFISSensors:
    def __init__(
        self,
        debug: bool = False,
        smoothing_factor: float = 0.2,
        fault_mode: str = "warn",  # "silent", "warn", "exception"
        log_faults: bool = True,
        log_file: str = "efis_fault_log.txt",
        pressure_range_hpa=(800.0, 1100.0),
        altitude_range_m=(-300.0, 6000.0),
        voltage_range_v=(0.0, 5.2),
        sensor_timeout_s: float = 2.0
    ):
        """
        Initialize sensors and internal state.

        :param smoothing_factor: EMA alpha in (0,1). Higher = more responsive.
        :param fault_mode: "silent", "warn", or "exception".
        :param log_faults: write faults/warnings to log_file when True.
        :param sensor_timeout_s: seconds to consider a sensor stale if not updated.
        """

        self.debug = debug
        self.SM = float(smoothing_factor)
        assert 0.0 < self.SM <= 1.0, "smoothing_factor must be in (0,1]"

        self.fault_mode = fault_mode
        assert self.fault_mode in ("silent", "warn", "exception")

        # ranges and timeout
        self.pressure_min, self.pressure_max = pressure_range_hpa
        self.alt_min, self.alt_max = altitude_range_m
        self.volt_min, self.volt_max = voltage_range_v
        self.timeout = float(sensor_timeout_s)

        # logging
        self.log_faults = bool(log_faults)
        self.log_file = log_file
        self._setup_logger()

        # I2C & devices
        self.i2c = None
        self.bno = None
        self.mpr = None
        self.ads1 = None
        self.ads2 = None
        self.ch1 = None
        self.ch2 = None
        self.ch3 = None
        self.ch4 = None

        # smoothed values
        self._pressure_smooth = None
        self._altitude_smooth = None
        self._analog_smooth = {"sensor1": None, "sensor2": None, "sensor3": None, "sensor4": None}

        # last update timestamps (epoch seconds)
        now = time.time()
        self._last = {
            "bno085": None,
            "mprls": None,
            "ads1015_1": None,
            "ads1015_2": None,
            "i2c": now
        }

        # status dict placeholders
        self._status = {
            "bno085": {"status": "UNKNOWN", "last_update": None, "error": None},
            "mprls": {"status": "UNKNOWN", "last_update": None, "error": None},
            "ads1015_1": {"status": "UNKNOWN", "last_update": None, "error": None},
            "ads1015_2": {"status": "UNKNOWN", "last_update": None, "error": None},
            "i2c": {"status": "UNKNOWN", "last_update": now, "error": None},
        }

        # initialize I2C and devices
        try:
            self._init_i2c()
            self._init_bno085()
            self._init_mprls()
            self._init_ads1015()
        except Exception as e:
            # initialization errors are handled via status and logging
            self._handle_fault("i2c", f"I2C init error: {e}")

    # --------------------------
    # Logger setup
    # --------------------------
    def _setup_logger(self):
        self._logger = logging.getLogger("EFISensors")
        self._logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        # avoid duplicate handlers if re-initialized
        if not self._logger.handlers:
            fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
            if self.log_faults:
                fh = logging.FileHandler(self.log_file)
                fh.setLevel(logging.INFO)
                fh.setFormatter(fmt)
                self._logger.addHandler(fh)
            # console handler for warnings/exceptions in warn/exception modes
            ch = logging.StreamHandler()
            ch.setFormatter(fmt)
            self._logger.addHandler(ch)

    # --------------------------
    # I2C initialization
    # --------------------------
    def _init_i2c(self):
        if self.debug: print("[INFO] Initializing I2C...")
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            # wait for bus ready (non-blocking in a polite loop)
            start = time.time()
            while not self.i2c.try_lock():
                time.sleep(0.05)
                if time.time() - start > 5:
                    raise RuntimeError("I2C bus lock timeout")
            self._status["i2c"].update({"status": "OK", "last_update": time.time(), "error": None})
            if self.debug: print("[OK] I2C ready")
        except Exception as e:
            self._status["i2c"].update({"status": "FAULT", "last_update": time.time(), "error": str(e)})
            self._handle_fault("i2c", f"I2C initialization failed: {e}")

    # --------------------------
    # Device inits
    # --------------------------
    def _init_bno085(self):
        if self.debug: print("[INFO] Initializing BNO085...")
        try:
            self.bno = BNO08X_I2C(self.i2c, address=0x4B)
            # enable commonly used reports
            self.bno.enable_feature(adafruit_bno08x.BNO_REPORT_ACCELEROMETER)
            self.bno.enable_feature(adafruit_bno08x.BNO_REPORT_GYROSCOPE)
            self.bno.enable_feature(adafruit_bno08x.BNO_REPORT_MAGNETOMETER)
            self.bno.enable_feature(adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR)
            self._status["bno085"].update({"status": "OK", "last_update": time.time(), "error": None})
            if self.debug: print("[OK] BNO085 init")
        except Exception as e:
            self.bno = None
            self._status["bno085"].update({"status": "MISSING", "last_update": None, "error": str(e)})
            self._handle_fault("bno085", f"BNO085 init failed: {e}")

    def _init_mprls(self):
        if self.debug: print("[INFO] Initializing MPRLS...")
        try:
            # adjust psi_min/psi_max depending on your part (default here matches many breakouts)
            self.mpr = adafruit_mprls.MPRLS(self.i2c, psi_min=0, psi_max=25)
            self._status["mprls"].update({"status": "OK", "last_update": time.time(), "error": None})
            if self.debug: print("[OK] MPRLS init")
        except Exception as e:
            self.mpr = None
            self._status["mprls"].update({"status": "MISSING", "last_update": None, "error": str(e)})
            self._handle_fault("mprls", f"MPRLS init failed: {e}")

    def _init_ads1015(self):
        if self.debug: print("[INFO] Initializing ADS1015 ADCs...")
        # ADS1015 #1 at 0x48
        try:
            self.ads1 = ADS1015(self.i2c, address=0x48)
            self.ch1 = AnalogIn(self.ads1, ADS1015.P0)
            self.ch2 = AnalogIn(self.ads1, ADS1015.P1)
            self._status["ads1015_1"].update({"status": "OK", "last_update": time.time(), "error": None})
            if self.debug: print("[OK] ADS1015 #1 init")
        except Exception as e:
            self.ads1 = None
            self.ch1 = self.ch2 = None
            self._status["ads1015_1"].update({"status": "MISSING", "last_update": None, "error": str(e)})
            self._handle_fault("ads1015_1", f"ADS1015 #1 init failed: {e}")

        # ADS1015 #2 at 0x49
        try:
            self.ads2 = ADS1015(self.i2c, address=0x49)
            self.ch3 = AnalogIn(self.ads2, ADS1015.P0)
            self.ch4 = AnalogIn(self.ads2, ADS1015.P1)
            self._status["ads1015_2"].update({"status": "OK", "last_update": time.time(), "error": None})
            if self.debug: print("[OK] ADS1015 #2 init")
        except Exception as e:
            self.ads2 = None
            self.ch3 = self.ch4 = None
            self._status["ads1015_2"].update({"status": "MISSING", "last_update": None, "error": str(e)})
            self._handle_fault("ads1015_2", f"ADS1015 #2 init failed: {e}")

    # --------------------------
    # Smoothing helper
    # --------------------------
    def _smooth(self, prev, new):
        if prev is None:
            return new
        return (self.SM * new) + ((1.0 - self.SM) * prev)

    # --------------------------
    # Fault handling / logging
    # --------------------------
    def _timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _log(self, level: str, message: str):
        """Log to file (if enabled) and to console via logger."""
        # level: "INFO", "WARN", "FAULT", "ERROR"
        if level.upper() in ("WARN", "WARNING"):
            self._logger.warning(message)
        elif level.upper() in ("FAULT", "ERROR"):
            self._logger.error(message)
        else:
            self._logger.info(message)

    def _handle_fault(self, key: str, message: str):
        """Handle a fault based on configured fault_mode and update status dict/log."""
        ts = time.time()
        # update status dict
        self._status.setdefault(key, {})
        self._status[key].update({
            "status": "FAULT",
            "last_update": None,
            "error": message
        })

        # log with timestamp and desired level
        log_msg = f"{key}: {message}"
        if self.log_faults:
            self._log("FAULT", log_msg)

        if self.fault_mode == "warn":
            print(f"[WARN] {self._timestamp()} - {log_msg}")
        elif self.fault_mode == "exception":
            raise SensorFault(log_msg)
        # silent just stores status and (optionally) logs to file

    def _handle_warn(self, key: str, message: str):
        """Handle a non-critical warning (e.g., out-of-range but not fatal)."""
        self._status.setdefault(key, {})
        self._status[key].update({
            "status": "WARN",
            "last_update": self._status[key].get("last_update"),
            "error": message
        })
        if self.log_faults:
            self._log("WARN", f"{key}: {message}")
        if self.fault_mode == "warn":
            print(f"[WARN] {self._timestamp()} - {key}: {message}")
        elif self.fault_mode == "exception":
            raise SensorFault(f"{key}: {message}")

    # --------------------------
    # Update / read methods
    # --------------------------
    def update_all(self):
        """
        Poll all sensors, update smoothed values, timestamps, and run checks.
        Call this periodically from your main loop (e.g., 5–100 Hz depending on needs).
        """
        now = time.time()
        # BNO085
        if self.bno:
            try:
                q = self.bno.quaternion  # reading this property ensures IMU is alive
                self._last["bno085"] = now
                self._status["bno085"].update({"status": "OK", "last_update": now, "error": None})
            except Exception as e:
                self._handle_fault("bno085", f"Read error: {e}")

        # MPRLS pressure
        if self.mpr:
            try:
                raw_p = float(self.mpr.pressure)  # hPa
                self._last["mprls"] = now
                self._status["mprls"].update({"status": "OK", "last_update": now, "error": None})

                # smoothing
                self._pressure_smooth = self._smooth(self._pressure_smooth, raw_p)

                # range check
                if not (self.pressure_min <= raw_p <= self.pressure_max):
                    self._handle_warn("mprls", f"Pressure out-of-range: {raw_p:.2f} hPa")
            except Exception as e:
                self._handle_fault("mprls", f"Read error: {e}")

        # ADS1015 #1
        if self.ads1 and self.ch1 and self.ch2:
            try:
                v1 = float(self.ch1.voltage)
                v2 = float(self.ch2.voltage)
                self._last["ads1015_1"] = now
                self._status["ads1015_1"].update({"status": "OK", "last_update": now, "error": None})

                # smoothing
                self._analog_smooth["sensor1"] = self._smooth(self._analog_smooth["sensor1"], v1)
                self._analog_smooth["sensor2"] = self._smooth(self._analog_smooth["sensor2"], v2)

                # range check (allow small tolerance above max)
                if not (self.volt_min <= v1 <= self.volt_max):
                    self._handle_warn("ads1015_1", f"Sensor1 voltage out-of-range: {v1:.3f} V")
                if not (self.volt_min <= v2 <= self.volt_max):
                    self._handle_warn("ads1015_1", f"Sensor2 voltage out-of-range: {v2:.3f} V")
            except Exception as e:
                self._handle_fault("ads1015_1", f"Read error: {e}")

        # ADS1015 #2
        if self.ads2 and self.ch3 and self.ch4:
            try:
                v3 = float(self.ch3.voltage)
                v4 = float(self.ch4.voltage)
                self._last["ads1015_2"] = now
                self._status["ads1015_2"].update({"status": "OK", "last_update": now, "error": None})

                self._analog_smooth["sensor3"] = self._smooth(self._analog_smooth["sensor3"], v3)
                self._analog_smooth["sensor4"] = self._smooth(self._analog_smooth["sensor4"], v4)

                if not (self.volt_min <= v3 <= self.volt_max):
                    self._handle_warn("ads1015_2", f"Sensor3 voltage out-of-range: {v3:.3f} V")
                if not (self.volt_min <= v4 <= self.volt_max):
                    self._handle_warn("ads1015_2", f"Sensor4 voltage out-of-range: {v4:.3f} V")
            except Exception as e:
                self._handle_fault("ads1015_2", f"Read error: {e}")

        # Derived altitude smoothing & range check (if pressure available)
        if self._pressure_smooth is not None:
            alt = 44330.0 * (1 - (self._pressure_smooth / 1013.25) ** 0.1903)
            self._altitude_smooth = self._smooth(self._altitude_smooth, alt)
            # altitude range check on raw derived alt
            if not (self.alt_min <= alt <= self.alt_max):
                self._handle_warn("mprls", f"Derived altitude out-of-range: {alt:.1f} m")

        # timeout/staleness checks
        self._check_timeouts()

    def _check_timeouts(self):
        """Mark sensors FAULT if no update within timeout window."""
        now = time.time()
        for key in ("bno085", "mprls", "ads1015_1", "ads1015_2"):
            last = self._last.get(key)
            if last is None:
                # if sensor was never updated, leave as-is (MISSING handled earlier)
                continue
            if now - last > self.timeout:
                # stale sensor
                self._handle_fault(key, f"No update for {now - last:.1f}s (timeout={self.timeout}s)")

    # --------------------------
    # Data retrieval helpers
    # --------------------------
    def get_orientation(self):
        """Return latest quaternion (x,y,z,w) or None."""
        if self.bno:
            try:
                return self.bno.quaternion
            except Exception:
                return None
        return None

    def get_pressure_hpa(self):
        """Return smoothed hPa or None."""
        return self._pressure_smooth

    def get_pressure_inhg(self):
        p = self.get_pressure_hpa()
        return self.hpa_to_inhg(p) if p is not None else None

    def get_altitude_m(self):
        """Return smoothed altitude in meters or None."""
        return self._altitude_smooth

    def get_altitude_ft(self):
        m = self.get_altitude_m()
        return self.m_to_ft(m) if m is not None else None

    def get_analog_voltages(self):
        """Return dict of smoothed analog voltages (sensor1..sensor4)"""
        return dict(self._analog_smooth)

    # --------------------------
    # Status and utility methods
    # --------------------------
    def get_status(self):
        """Return a copy of the status dictionary with readable timestamps."""
        status_copy = {}
        for k, v in self._status.items():
            s = dict(v)  # shallow copy
            if s.get("last_update"):
                s["last_update"] = datetime.datetime.fromtimestamp(s["last_update"]).isoformat()
            status_copy[k] = s
        return status_copy

    def all_systems_ok(self) -> bool:
        """Return True only if all sensors report OK (no WARN/FAULT/MISSING)."""
        for k, v in self._status.items():
            if v.get("status") != "OK":
                return False
        return True

    # --------------------------
    # Unit conversion helpers
    # --------------------------
    @staticmethod
    def hpa_to_inhg(hpa: float) -> float:
        return hpa * 0.0295299830714

    @staticmethod
    def inhg_to_hpa(inhg: float) -> float:
        return inhg / 0.0295299830714

    @staticmethod
    def m_to_ft(m: float) -> float:
        return m * 3.28084

    @staticmethod
    def ft_to_m(ft: float) -> float:
        return ft / 3.28084

    @staticmethod
    def volts_to_percent(voltage: float, v_ref: float = 5.0) -> float:
        return (voltage / v_ref) * 100.0

    # --------------------------
    # Cleanup
    # --------------------------
    def close(self):
        """Release I2C lock and clean up."""
        try:
            if self.i2c:
                self.i2c.unlock()
        except Exception:
            pass
        # update status to indicate shutdown
        for k in self._status:
            self._status[k]["status"] = self._status[k].get("status", "UNKNOWN")
        if self.debug:
            print("[INFO] EFISSensors closed.")

# --------------------------
# Standalone test
# --------------------------
if __name__ == "__main__":
    sensors = EFISSensors(debug=True, smoothing_factor=0.2, fault_mode="warn", log_faults=True)

    try:
        print("Starting periodic update loop (Ctrl+C to stop)...")
        while True:
            sensors.update_all()
            # display values
            p_hpa = sensors.get_pressure_hpa()
            p_inhg = sensors.get_pressure_inhg() if p_hpa else None
            alt_m = sensors.get_altitude_m()
            alt_ft = sensors.get_altitude_ft() if alt_m else None
            analog = sensors.get_analog_voltages()
            status = sensors.get_status()

            print(f"Pressure: {p_hpa:.2f} hPa" if p_hpa else "Pressure: N/A", end="  |  ")
            print(f"{p_inhg:.2f} inHg" if p_inhg else "N/A", end="  ||  ")
            print(f"Alt: {alt_m:.1f} m / {alt_ft:.0f} ft" if alt_m else "Alt: N/A", end="  ||  ")
            print("Analog:", {k: (f"{v:.3f} V" if v is not None else None) for k, v in analog.items()})
            print("Status:", status)
            print("-" * 80)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Exiting test loop.")
    finally:
        sensors.close()
