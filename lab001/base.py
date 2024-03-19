#!/usr/bin/env python3

from migen import *

from litex.build.generic_platform import *
from litex_boards.platforms import colorlight_i5

# Create our platform (fpga interface)
platform = colorlight_i5.Platform("i9", "7.2")
led = platform.request("user_led_n", 0)

# Create our module (fpga description)
module = Module()

# Create a counter and blink a led
counter = Signal(26)
module.comb += led.eq(counter[25])
module.sync += counter.eq(counter + 1)

# Build --------------------------------------------------------------------------------------------

platform.build(module)

prog = platform.create_programmer()
prog.load_bitstream("build/top.bit")
