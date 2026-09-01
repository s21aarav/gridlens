"""Graph repository interface and Neo4j implementation for substation topology facts."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from domain.models.equipment import Substation, Feeder, Breaker, Relay, IED, Sensor, Bus, Transformer
from domain.models.results import TopologyQueryResult


class GraphRepository(ABC):
    """Abstract interface for querying engineering topology and equipment relationships."""

    @abstractmethod
    async def get_feeder_protection_chain(self, feeder_id: str) -> TopologyQueryResult:
        pass

    @abstractmethod
    async def get_equipment_relationships(self, equipment_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_sensor_bindings(self, ied_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_substation_topology(self, substation_id: str = "OGS-01") -> Dict[str, Any]:
        pass


class Neo4jGraphRepository(GraphRepository):
    """Neo4j-backed graph repository with fallback support for in-memory graph store."""

    def __init__(self, neo4j_uri: Optional[str] = None, auth: Optional[tuple] = None):
        self.uri = neo4j_uri
        self.auth = auth
        self._driver = None
        # Internal structured topology store representing Orion Grid Substation OGS-01
        self._seed_data: Dict[str, Any] = self._build_ogs01_topology()

    def _build_ogs01_topology(self) -> Dict[str, Any]:
        return {
            "substation": {"id": "OGS-01", "name": "Orion Grid Substation OGS-01"},
            "buses": [
                {"bus_id": "BUS_A", "name": "33kV Bus A", "voltage_kv": 33.0},
                {"bus_id": "BUS_B", "name": "11kV Bus B", "voltage_kv": 11.0},
            ],
            "transformers": [
                {
                    "transformer_id": "T1",
                    "name": "33/11kV 25MVA Power Transformer T1",
                    "primary_bus": "BUS_A",
                    "secondary_bus": "BUS_B",
                    "rated_mva": 25.0,
                }
            ],
            "feeders": {
                "F12": {
                    "feeder_id": "F12",
                    "name": "Feeder F12 (North Industrial Feeder)",
                    "bay_id": "BAY_F12",
                    "connected_bus_id": "BUS_B",
                    "primary_relay_id": "RELAY_12",
                    "controlled_breaker_id": "CB12",
                    "ied_id": "IED_12",
                    "sensor_ids": ["CT12A", "CT12B", "CT12C", "VT12"],
                    "upstream_transformer_id": "T1",
                    "downstream_equipment": ["Industrial Park Substation", "Refinery Pumping Load"],
                    "is_topology_complete": True,
                },
                "F13": {
                    "feeder_id": "F13",
                    "name": "Feeder F13 (South Commercial Feeder)",
                    "bay_id": "BAY_F13",
                    "connected_bus_id": "BUS_B",
                    "primary_relay_id": "RELAY_13",
                    "controlled_breaker_id": "CB13",
                    "ied_id": "IED_13",
                    "sensor_ids": ["CT13A", "CT13B", "CT13C", "VT13"],
                    "upstream_transformer_id": "T1",
                    "downstream_equipment": ["City Hospital Feeder", "Metro Station Bay"],
                    "is_topology_complete": True,
                }
            },
            "breakers": {
                "CB12": {"breaker_id": "CB12", "bay_id": "BAY_F12", "rated_current_a": 2000.0, "state": "CLOSED"},
                "CB13": {"breaker_id": "CB13", "bay_id": "BAY_F13", "rated_current_a": 2000.0, "state": "CLOSED"},
            },
            "relays": {
                "RELAY_12": {
                    "relay_id": "RELAY_12",
                    "name": "SIPROTEC 5 Protection Relay R12",
                    "ied_id": "IED_12",
                    "bay_id": "BAY_F12",
                    "protected_feeder_id": "F12",
                    "controlled_breaker_id": "CB12",
                    "active_functions": ["50", "51", "50N", "51N", "27", "59"],
                    "pickup_current_a": 2500.0,
                },
                "RELAY_13": {
                    "relay_id": "RELAY_13",
                    "name": "SIPROTEC 5 Protection Relay R13",
                    "ied_id": "IED_13",
                    "bay_id": "BAY_F13",
                    "protected_feeder_id": "F13",
                    "controlled_breaker_id": "CB13",
                    "active_functions": ["50", "51", "50N", "51N"],
                    "pickup_current_a": 2200.0,
                }
            },
            "ieds": {
                "IED_12": {
                    "ied_id": "IED_12",
                    "name": "Bay Controller & Protection IED-12",
                    "model": "SIPROTEC 5 - 7SJ85",
                    "bay_id": "BAY_F12",
                    "ct_channel_mapping": {"CH1": "CT12A", "CH2": "CT12B", "CH3": "CT12C"},
                    "vt_channel_mapping": {"CH4": "VT12"},
                },
                "IED_13": {
                    "ied_id": "IED_13",
                    "name": "Bay Controller & Protection IED-13",
                    "model": "SIPROTEC 5 - 7SJ85",
                    "bay_id": "BAY_F13",
                    "ct_channel_mapping": {"CH1": "CT13A", "CH2": "CT13B", "CH3": "CT13C"},
                    "vt_channel_mapping": {"CH4": "VT13"},
                }
            },
            "sensors": {
                "CT12A": {"sensor_id": "CT12A", "phase": "A", "ratio": 240.0, "primary": 1200, "secondary": 5, "bay_id": "BAY_F12"},
                "CT12B": {"sensor_id": "CT12B", "phase": "B", "ratio": 240.0, "primary": 1200, "secondary": 5, "bay_id": "BAY_F12"},
                "CT12C": {"sensor_id": "CT12C", "phase": "C", "ratio": 240.0, "primary": 1200, "secondary": 5, "bay_id": "BAY_F12"},
                "VT12":  {"sensor_id": "VT12",  "phase": "A", "ratio": 100.0, "primary": 11000, "secondary": 110, "bay_id": "BAY_F12"},
                "CT13A": {"sensor_id": "CT13A", "phase": "A", "ratio": 240.0, "primary": 1200, "secondary": 5, "bay_id": "BAY_F13"},
                "CT13B": {"sensor_id": "CT13B", "phase": "B", "ratio": 240.0, "primary": 1200, "secondary": 5, "bay_id": "BAY_F13"},
                "CT13C": {"sensor_id": "CT13C", "phase": "C", "ratio": 240.0, "primary": 1200, "secondary": 5, "bay_id": "BAY_F13"},
                "VT13":  {"sensor_id": "VT13",  "phase": "A", "ratio": 100.0, "primary": 11000, "secondary": 110, "bay_id": "BAY_F13"},
            }
        }

    async def get_feeder_protection_chain(self, feeder_id: str) -> TopologyQueryResult:
        clean_id = feeder_id.upper().strip()
        feeder_data = self._seed_data["feeders"].get(clean_id)
        if not feeder_data:
            # Check if user specified bay or relay name
            for f_k, f_v in self._seed_data["feeders"].items():
                if f_k in clean_id or f_v["bay_id"] in clean_id:
                    feeder_data = f_v
                    break
        
        if not feeder_data:
            return TopologyQueryResult(
                feeder_id=feeder_id,
                bay_id="UNKNOWN_BAY",
                connected_bus_id="UNKNOWN_BUS",
                primary_relay_id="UNKNOWN_RELAY",
                controlled_breaker_id="UNKNOWN_BREAKER",
                ied_id="UNKNOWN_IED",
                is_topology_complete=False,
                metadata={"error": f"Feeder {feeder_id} not found in Substation OGS-01 graph."},
            )

        return TopologyQueryResult(
            feeder_id=feeder_data["feeder_id"],
            bay_id=feeder_data["bay_id"],
            connected_bus_id=feeder_data["connected_bus_id"],
            primary_relay_id=feeder_data["primary_relay_id"],
            controlled_breaker_id=feeder_data["controlled_breaker_id"],
            ied_id=feeder_data["ied_id"],
            sensor_ids=feeder_data["sensor_ids"],
            upstream_transformer_id=feeder_data.get("upstream_transformer_id"),
            downstream_equipment=feeder_data.get("downstream_equipment", []),
            is_topology_complete=True,
            metadata={"source": "Seeded OGS-01 topology repository", "backend": "in-memory"},
        )

    async def get_equipment_relationships(self, equipment_id: str) -> Dict[str, Any]:
        eq_upper = equipment_id.upper().strip()
        # Search all equipment categories
        for cat in ["feeders", "breakers", "relays", "ieds", "sensors"]:
            if eq_upper in self._seed_data[cat]:
                return {"entity_type": cat[:-1], "details": self._seed_data[cat][eq_upper]}
        return {"error": f"Equipment {equipment_id} not found"}

    async def get_sensor_bindings(self, ied_id: str) -> List[Dict[str, Any]]:
        ied_data = self._seed_data["ieds"].get(ied_id.upper().strip())
        if not ied_data:
            return []
        bindings = []
        for ch, s_id in ied_data.get("ct_channel_mapping", {}).items():
            s_data = self._seed_data["sensors"].get(s_id, {})
            bindings.append({"channel": ch, "sensor_id": s_id, "type": "CT", **s_data})
        for ch, s_id in ied_data.get("vt_channel_mapping", {}).items():
            s_data = self._seed_data["sensors"].get(s_id, {})
            bindings.append({"channel": ch, "sensor_id": s_id, "type": "VT", **s_data})
        return bindings

    async def get_substation_topology(self, substation_id: str = "OGS-01") -> Dict[str, Any]:
        return self._seed_data
