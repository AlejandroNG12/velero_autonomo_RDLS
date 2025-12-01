# mavlink/connection.py

from pymavlink import mavutil
from config import settings


class PixhawkConnection:
    """
    Abstrae la conexión MAVLink a la Pixhawk 6X desde la Raspberry Pi.
    """

    def __init__(self, connection_string: str | None = None):
        if connection_string is None:
            connection_string = settings.CONNECTION_STRING

        self.connection_string = connection_string
        self.master = None

    def connect(self):
        """
        Abre la conexión y espera al primer heartbeat.
        """
        conn = self.connection_string

        if conn.startswith("serial:"):
            _, dev, baud = conn.split(":")
            baud = int(baud)
            print(f"[INFO] Conectando por serie a {dev} @ {baud} baud...")
            self.master = mavutil.mavlink_connection(
                dev,
                baud=baud,
                source_system=settings.SYSID,
            )
        elif conn.startswith("udp:"):
            # Ejemplo: "udp:0.0.0.0:14551"
            _, ip, port = conn.split(":")
            print(f"[INFO] Conectando por UDP a {ip}:{port} ...")
            self.master = mavutil.mavlink_connection(
                f"udp:{ip}:{port}",
                source_system=settings.SYSID,
            )
        else:
            raise ValueError(f"Connection string no reconocida: {conn}")

        print("[INFO] Esperando heartbeat de la Pixhawk...")
        self.master.wait_heartbeat(timeout=settings.HEARTBEAT_TIMEOUT)
        print(
            f"[OK] Heartbeat recibido de sistema {self.master.target_system}, "
            f"componente {self.master.target_component}"
        )
        return self.master

    def get_master(self):
        if self.master is None:
            raise RuntimeError("No hay conexión abierta. Llama a connect() primero.")
        return self.master
