#!/usr/bin/env python3

# python3 -m litex_boards.targets.colorlight_i5 --board i9 --revision 7.2 --cpu-type None \
#   --with-video-colorbars --video-timing 1024x768@60Hz --build --load --ecppack-compress

from migen import *

from litex_boards.platforms import colorlight_i5
from litex_boards.targets.colorlight_i5 import _CRG

from litex.soc.integration.soc_core import SoCCore
from litex.soc.integration.builder import Builder
from litex.soc.cores.video import VideoHDMIPHY, VideoTimingGenerator, ColorBarsPattern
from litex.soc.cores.video import video_timings

class BaseSoC(SoCCore):
    def __init__(self):
        platform = colorlight_i5.Platform("i9", "7.2")
        video_timing = "800x600@60Hz"
        sys_clk_freq = 60e6

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
        video_colorbars = ClockDomainsRenamer("hdmi")(ColorBarsPattern())
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
