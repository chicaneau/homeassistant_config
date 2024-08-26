"""Tuya Dimmer TS110E."""
from typing import Optional, Union
from zigpy.profiles import zgp, zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    NoManufacturerCluster,
    TuyaDimmerSwitch,
    #TuyaZBExternalSwitchTypeCluster,
	TuyaManufCluster,
)
from zhaquirks.tuya.mcu import (
    TuyaInWallLevelControl,
    TuyaLevelControlManufCluster,
    TuyaOnOff,
    TuyaOnOffNM,
)

#class TuyaInWallLevelControlNM(NoManufacturerCluster, TuyaInWallLevelControl):
#    """Tuya Level cluster for inwall dimmable device with NoManufacturerID."""

TUYA_LEVEL_ATTRIBUTE = 0xF000
TUYA_BULB_TYPE_ATTRIBUTE = 0xFC02
TUYA_MIN_LEVEL_ATTRIBUTE = 0xFC03
TUYA_MAX_LEVEL_ATTRIBUTE = 0xFC04
TUYA_CUSTOM_LEVEL_COMMAND = 0x00F0


class TuyaLevelPayload(t.Struct):
    """Tuya Level payload."""

    level: t.uint16_t
    transtime: t.uint16_t
    def __init__(self, level, transtime):
        self.level = level
        self.transtime = transtime

    def to_dict(self):
        return self.__dict__

class TuyaBulbType(t.enum8):
    """Tuya bulb type."""

    LED = 0x00
    INCANDESCENT = 0x01
    HALOGEN = 0x02


class F000LevelControlCluster(NoManufacturerCluster, LevelControl):
    """LevelControlCluster that reports to attrid 0xF000."""

    server_commands = LevelControl.server_commands.copy()
    server_commands[TUYA_CUSTOM_LEVEL_COMMAND] = foundation.ZCLCommandDef(
        "moveToLevelTuya",
        #(TuyaLevelPayload,),
		{
            "payload": TuyaLevelPayload
        },
        is_manufacturer_specific=False,
    )

    attributes = LevelControl.attributes.copy()
    attributes.update(
        {
            # 0xF000
            TUYA_LEVEL_ATTRIBUTE: ("manufacturer_current_level", t.uint16_t),
            # 0xFC02
            TUYA_BULB_TYPE_ATTRIBUTE: ("bulb_type", TuyaBulbType),
            # 0xFC03
            TUYA_MIN_LEVEL_ATTRIBUTE: ("manufacturer_min_level", t.uint16_t),
            # 0xFC04
            TUYA_MAX_LEVEL_ATTRIBUTE: ("manufacturer_max_level", t.uint16_t),
        }
    )

    # 0xF000 reported values are 10-1000, convert to 0-254
    def _update_attribute(self, attrid, value):
        if attrid == TUYA_LEVEL_ATTRIBUTE:
            self.debug(
                "Getting brightness %s",
                value,
            )
            value = (value + 4 - 10) * 254 // (1000 - 10)
            attrid = 0x0000

        super()._update_attribute(attrid, value)

    async def command(
        self,
        command_id: Union[foundation.GeneralCommand, int, t.uint8_t],
        *args,
        manufacturer: Optional[Union[int, t.uint16_t]] = None,
        expect_reply: bool = True,
        tsn: Optional[Union[int, t.uint8_t]] = None,
        **kwargs,
    ):
        """Override the default Cluster command."""
        self.debug(
            "Sending Cluster Command. Cluster Command is %x, Arguments are %s",
            command_id,
            args,
        )

        # Extract level and transtime from kwargs
        level = kwargs.pop('level', None)
        transtime = kwargs.pop('transtime', 0)

        # move_to_level, move, move_to_level_with_on_off
        if command_id in (0x0000, 0x0001, 0x0004):
            if level is not None:
                # convert dim values to 10-1000
                #brightness = args[0] * (1000 - 10) // 254 + 10
                brightness = level * (1000 - 10) // 254 + 10
                self.debug(
                    "Setting brightness to %s",
                    brightness,
                )
                payload = TuyaLevelPayload(level=brightness, transtime=transtime)
                return await super().command(
                    TUYA_CUSTOM_LEVEL_COMMAND,
                    payload,
                    #TuyaLevelPayload(level=brightness, transtime=0),
                    manufacturer=manufacturer,
                    expect_reply=expect_reply,
                    tsn=tsn,
                    #**kwargs
                )
            else:
                raise ValueError("Missing required argument: 'level'")

        return super().command(command_id, *args, manufacturer, expect_reply, tsn)#, **kwargs

#class F000OnOffCluster(OnOff):
#    """Custom OnOff Cluster with redefined attribute."""
#
#    attributes = OnOff.attributes.copy()
#    attributes.update({
#        0xf000: ("on_off", t.uint32_t),
#        #0xf000: OnOff.attributes[0x0000]
#    })
#    del attributes[0x0000]

class DimmerSwitchWithNeutral1GangVar02(TuyaDimmerSwitch):
    """Tuya Dimmer Switch Module With Neutral 1 Gang."""

    signature = {
        MODELS_INFO: [("_TZ3210_k1msuvg6", "TS110Etest")],
        ENDPOINTS: {
            1: {
                # "profile_id": 260,
                # "device_type": "0x0101",
                # "in_clusters": ["0x0000","0x0003","0x0004","0x0005","0x0006","0x0008","0xef00",],
                # "out_clusters": ["0x000a","0x0019"]
                PROFILE_ID: zha.PROFILE_ID,
                #DEVICE_TYPE: 101,
				DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    TuyaManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # "profile_id": 41440,
                # "device_type": "0x0061",
                # "in_clusters": [],
                # "out_clusters": ["0x0021"]
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,			
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    F000LevelControlCluster,
                    TuyaLevelControlManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                DEVICE_TYPE: zgp.PROFILE_ID,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }