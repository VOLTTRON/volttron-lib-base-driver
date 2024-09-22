from datetime import timedelta
from enum import Enum
from pydantic import BaseModel, computed_field, ConfigDict, Field, field_validator

# TODO: Wire up the data_source field to poll scheduling (everything is currently short-poll because this isn't used).
# TODO: Should NEVER actually be an option? Could it just be None?
class DataSource(Enum):
    SHORT_POLL = "short_poll"
    LONG_POLL = "long_poll"
    NEVER = "never"
    POLL_ONCE = "poll_once"
    STATIC = "static"


class EquipmentConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)
    active: bool = True
    group: str | None = None
    meta_data: dict = {}
    # TODO: If this needs to be an int, we may need to use milliseconds someplace.
    polling_interval: int | None = Field(default=None, alias='interval')
    publish_single_depth: bool | None = Field(default=None, alias='publish_depth_first_single')
    publish_single_breadth: bool | None = Field(default=None, alias='publish_breadth_first_single')
    publish_multi_depth: bool | None = Field(default=None, alias='publish_depth_first_multi')
    publish_multi_breadth: bool | None = Field(default=None, alias='publish_breadth_first_multi')
    publish_all_depth: bool | None = Field(default=None, alias='publish_depth_first_all')
    publish_all_breadth: bool | None = Field(default=None, alias='publish_breadth_first_all')
    reservation_required_for_write: bool = False

    # TODO: Why can't this parse empty strings as numbers with this validator?
    @classmethod
    @field_validator('polling_interval', mode='before')
    def _normalize_polling_interval(cls, v):
        # TODO: This does not match int above, but we may need to convert to ms in calculations.
        return None if v == '' else float(v)

class PointConfig(EquipmentConfig):
    data_source: DataSource = Field(default='short_poll', alias='Data Source')
    reference_point_name: str = Field(default='', alias='Reference Point Name')
    volttron_point_name: str = Field(alias='Volttron Point Name')
    units: str = Field(default='', alias='Units')
    units_details: str = Field(default='', alias='Unit Details')
    configured_stale_timeout: float | None = Field(default=None, alias='stale_timeout')
    stale_timeout_multiplier: float = Field(default=3)
    writable: bool = Field(default=False, alias='Writable')
    notes: str = Field(default='', alias='Notes')

    @classmethod
    @field_validator('data_source', mode='before')
    def _normalize_data_source(cls, v):
        return v.lower()

    @computed_field
    @property
    def stale_timeout(self) -> timedelta | None:
        if self.configured_stale_timeout is None and self.polling_interval is None:
            return None
        else:
            return timedelta(seconds=(self.configured_stale_timeout
                    if self.configured_stale_timeout is not None
                    else self.polling_interval * self.stale_timeout_multiplier))

    @stale_timeout.setter
    def stale_timeout(self, value):
        self.configured_stale_timeout = value


class DeviceConfig(EquipmentConfig):
    all_publish_interval: float = 0.0
    allow_duplicate_remotes: bool = False
    equipment_specific_fields: dict = {}
    registry_config: list[PointConfig] = []


# TODO: Do we really need subclasses for the interfaces?
class RemoteConfig(BaseModel):
    model_config = ConfigDict(extra='allow', validate_assignment=True)
    driver_type: str
    heart_beat_point: str | None = None
    module: str | None = None