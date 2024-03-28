#!/usr/bin/env python3

from migen import *

from litex.build.generic_platform import *

from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.uart import UARTWishboneBridge
from litex.soc.cores import gpio

from litex_boards.platforms import colorlight_i5
from litex_boards.targets.colorlight_i5 import _CRG

class Led(gpio.GPIOOut):
    pass

# Design -------------------------------------------------------------------------------------------

# Create our platform (fpga interface)
platform = colorlight_i5.Platform("i9", "7.2")

# Create our soc (fpga description)
class BaseSoC(SoCMini):
    def __init__(self, platform, **kwargs):
        sys_clk_freq = int(100e6)

        # SoCMini (No CPU, we are controlling the SoC over UART)
        SoCMini.__init__(self, platform, sys_clk_freq, csr_data_width=32,
            ident="My first LiteX System On Chip", ident_version=True)

        # Clock Reset Generation
        self.submodules.crg = _CRG(platform, sys_clk_freq)

        # No CPU, use Serial to control Wishbone bus
        self.submodules.serial_bridge = UARTWishboneBridge(platform.request("serial"), sys_clk_freq)
        self.bus.add_master(master=self.serial_bridge.wishbone)

        # Led
        user_leds = Cat(*[platform.request("user_led_n", i) for i in range(1)])
        self.submodules.leds = Led(user_leds)
        self.add_csr("leds")

soc = BaseSoC(platform)

# Build --------------------------------------------------------------------------------------------

builder = Builder(soc, output_dir="build", csr_csv="test/csr.csv")
builder.build(build_name="top")

prog = platform.create_programmer()
prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))
