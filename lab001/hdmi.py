#!/usr/bin/env python3

# python3 -m litex_boards.targets.colorlight_i5 --board i9 --revision 7.2 --cpu-type None \
#   --with-video-colorbars --video-timing 1024x768@60Hz --build --load --ecppack-compress

from migen import *
from migen.genlib.cdc import MultiReg

from litex_boards.platforms import colorlight_i5
from litex_boards.targets.colorlight_i5 import _CRG

from litex.gen import *

from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.interconnect import stream
from litex.soc.cores.video import VideoHDMIPHY, VideoTimingGenerator
from litex.soc.cores.video import video_timings, video_data_layout, video_timing_layout, hbits

class ColorBarsPattern(LiteXModule):
    """Color Bars Pattern"""
    def __init__(self, video_timing, counter):
        self.enable   = Signal(reset=1)
        self.vtg_sink = vtg_sink   = stream.Endpoint(video_timing_layout)
        self.source   = source = stream.Endpoint(video_data_layout)

        hres = video_timings[video_timing]["h_active"]

        # # #

        enable = Signal()
        self.specials += MultiReg(self.enable, enable)

        # Control Path.
        pix_x = Signal(hbits)
        bar_x = Signal(3)

        fsm = FSM(reset_state="IDLE")
        fsm = ResetInserter()(fsm)
        self.fsm = fsm
        self.comb += fsm.reset.eq(~self.enable)
        fsm.act("IDLE",
            NextValue(pix_x, 0),
            NextValue(bar_x, 0),
            vtg_sink.ready.eq(1),
            If(vtg_sink.valid & vtg_sink.first & (vtg_sink.hcount == 0) & (vtg_sink.vcount == 0),
                vtg_sink.ready.eq(0),
                NextState("RUN")
            )
        )
        fsm.act("RUN",
            vtg_sink.connect(source, keep={"valid", "ready", "last", "de", "hsync", "vsync"}),
            If(source.valid & source.ready & source.de,
                NextValue(pix_x, pix_x + 1),
                If(pix_x == int(hres/7) - 1, # 7 Color Bars.
                    NextValue(pix_x, 0),
                    NextValue(bar_x, bar_x + 1)
                )
            ).Else(
                NextValue(pix_x, 0),
                NextValue(bar_x, 0)
            )
        )

        t = counter[17:25]

        # Data Path.
        color_bar = [
            # R     G     B
            [t, t, t], # White
            [0xff, 0xff, 0x00], # Yellow
            [0x00, 0xff, 0xff], # Cyan
            [0x00, 0xff, 0x00], # Green
            [0xff, 0x00, 0xff], # Purple
            [0xff, 0x00, 0x00], # Red
            [0x00, 0x00, 0xff], # Blue
            [0x00, 0x00, 0x00], # Black
        ]
        cases = {}
        for i in range(8):
            cases[i] = [
                source.r.eq(color_bar[i][0]),
                source.g.eq(color_bar[i][1]),
                source.b.eq(color_bar[i][2])
            ]
        self.comb += Case(bar_x, cases)

class BaseSoC(SoCCore):
    def __init__(self):
        platform = colorlight_i5.Platform("i9", "7.2")
        video_timing = "800x600@60Hz"
        sys_clk_freq = 60e6

        led = platform.request("user_led_n", 0)
        counter = Signal(26)
        self.comb += led.eq(counter[25])
        self.sync += counter.eq(counter + 1)

        self.crg = _CRG(platform, sys_clk_freq,
            with_video_pll   = True,
            pix_clk          = video_timings[video_timing]["pix_clk"]
        )

        SoCCore.__init__(self, platform, int(sys_clk_freq), ident="LiteX SoC on Colorlight i9", cpu_type=None)

        self.videophy = VideoHDMIPHY(platform.request("gpdi"), clock_domain="hdmi")

        # Video Timing Generator.
        video_colorbars_vtg = VideoTimingGenerator(default_video_timings=video_timing)
        video_colorbars_vtg = ClockDomainsRenamer("hdmi")(video_colorbars_vtg)
        self.add_module("video_colorbars_vtg", video_colorbars_vtg)

        # ColorsBars Pattern.
        video_colorbars = ColorBarsPattern(video_timing, counter)
        video_colorbars = ClockDomainsRenamer("hdmi")(video_colorbars)
        self.add_module("video_colorbars", video_colorbars)

        # Connect Video Timing Generator to ColorsBars Pattern.
        self.comb += [
            video_colorbars_vtg.source.connect(video_colorbars.vtg_sink),
            video_colorbars.source.connect(self.videophy.sink)
        ]

def main():
    soc = BaseSoC()

    builder = Builder(soc)
    builder.build(compress=True)

    prog = soc.platform.create_programmer()
    prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

if __name__ == "__main__":
    main()
