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
    def __init__(self):
        self.enable   = Signal(reset=1)
        self.vtg_sink = vtg_sink   = stream.Endpoint(video_timing_layout)
        self.source   = source = stream.Endpoint(video_data_layout)

        # hres = video_timings[video_timing]["h_active"]
        # vres = video_timings[video_timing]["v_active"]

        # # #

        self.fcount = Signal(8)

        enable = Signal()
        self.specials += MultiReg(self.enable, enable)

        fsm = FSM(reset_state="IDLE")
        fsm = ResetInserter()(fsm)
        self.fsm = fsm
        self.comb += fsm.reset.eq(~self.enable)
        fsm.act("IDLE",
            NextValue(self.fcount, 0),
            vtg_sink.ready.eq(1),
            If(vtg_sink.valid & vtg_sink.first & (vtg_sink.hcount == 0) & (vtg_sink.vcount == 0),
                vtg_sink.ready.eq(0),
                NextState("RUN")
            )
        )
        fsm.act("RUN",
            vtg_sink.connect(source, keep={"valid", "ready", "last", "de", "hsync", "vsync"}),
            If(vtg_sink.ready & (vtg_sink.hcount == 0) & (vtg_sink.vcount == 0),
                NextValue(self.fcount, self.fcount + 1),
            ),
        )

    def main_image(self):
        x = Signal((32, True))
        y = Signal((32, True))
        u = Signal((32, True))
        v = Signal((32, True))
        u2 = Signal((32, True))
        v2 = Signal((32, True))
        h = Signal((32, True))
        t = Signal((32, True))
        p = Signal((32, True))
        q = Signal((32, True))
        w0 = Signal((32, True))
        R0 = Signal((32, True))
        B0 = Signal((32, True))
        o = Signal((32, True))
        R1 = Signal((32, True))
        B1 = Signal((32, True))
        w1 = Signal((32, True))
        r = Signal((32, True))
        d = Signal((32, True))
        R2 = Signal((32, True))
        B2 = Signal((32, True))
        p1 = Signal((32, True))
        c = Signal((32, True))
        o1 = Signal((32, True))
        o2 = Signal((32, True))
        R3 = Signal((32, True))
        B3 = Signal((32, True))
        c1 = Signal((32, True))
        Ro = Signal((32, True))
        Bo = Signal((32, True))
        Rm = Signal((32, True))
        Bm = Signal((32, True))
        Go = Signal((32, True))
        self.comb += [
            x.eq(self.vtg_sink.hcount[3:] - 5),
            y.eq(self.vtg_sink.vcount[3:] - 10),
            u.eq(x - 36),
            v.eq(18 - y),
            u2.eq(u * u),
            v2.eq(v * v),
            h.eq(u2 + v2),
            If(h < 200,  # sphere
                t.eq(5200 + h*8),
                p.eq((t*u)>>7),
                q.eq((t*v)>>7),
                
                # bounce light
                w0.eq(18 + (((p*5-q*13))>>9)),
                If(w0 > 0,
                    R0.eq(420 + w0*w0)
                ).Else(
                    R0.eq(420),
                ),
                B0.eq(520),
                
                # sky light / ambient occlusion
                o.eq(q + 900),
                R1.eq((R0*o)>>12),
                B1.eq((B0*o)>>12),

                # sun/key light
                If(p > -q,
                    w1.eq((p+q)>>3),
                    Ro.eq(R1 + w1),
                    Bo.eq(B1 + w1),
                ).Else(
                    Ro.eq(R1),
                    Bo.eq(B1),
                )
            ).Elif(v < 0,  # ground
                R2.eq(150 + 2*v),
                B2.eq(50),
                
                p1.eq(h + 8*v2),
                c.eq(240*(-v) - p1),

                # sky light / ambient occlusion
                If(c > 1200,
                    o1.eq((25*c)>>3),
                    o2.eq((c*(7840-o1)>>9) - 8560),
                    R3.eq((R2*o2)>>10),
                    B3.eq((B2*o2)>>10),
                ).Else(
                    R3.eq(R2),
                    B3.eq(B2),
                ),

                # sun/key light with soft shadow
                r.eq(c + u*v),
                d.eq(3200 - h - 2*r),
                If(d > 0,
                    Ro.eq(R3 + d),
                ).Else(
                    Ro.eq(R3),
                ),
                Bo.eq(B3),
            ).Else(  # sky
                c1.eq(x + 4*y),
                Ro.eq(132 + c1),
                Bo.eq(192 + c1),
            ),
            If(Ro > 255,
                Rm.eq(255)
            ).Else(
                Rm.eq(Ro)
            ),
            If(Bo > 255,
                Bm.eq(255)
            ).Else(
                Bm.eq(Bo)
            ),
            Go.eq((Rm*11 + 5*Bm)>>4),
            self.source.r.eq(Rm[:8]),
            self.source.g.eq(Go[:8]),
            self.source.b.eq(Bm[:8]),
        ]

class BaseSoC(SoCCore):
    def __init__(self):
        platform = colorlight_i5.Platform("i9", "7.2")
        video_timing = "640x480@60Hz"
        sys_clk_freq = 25e6

        led = platform.request("user_led_n", 0)
        counter = Signal(26)
        self.comb += led.eq(counter[25])
        self.sync += counter.eq(counter + 1)

        self.crg = _CRG(platform, sys_clk_freq,
            with_video_pll   = True,
            pix_clk          = 25e6 # video_timings[video_timing]["pix_clk"]
        )

        SoCCore.__init__(self, platform, int(sys_clk_freq), ident="LiteX SoC on Colorlight i9", cpu_type=None)

        self.videophy = VideoHDMIPHY(platform.request("gpdi"), clock_domain="hdmi")

        # Video Timing Generator.
        video_colorbars_vtg = VideoTimingGenerator(default_video_timings=video_timing)
        video_colorbars_vtg = ClockDomainsRenamer("hdmi")(video_colorbars_vtg)
        self.add_module("video_colorbars_vtg", video_colorbars_vtg)

        # ColorsBars Pattern.
        video_colorbars = ColorBarsPattern()
        video_colorbars.main_image()
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
