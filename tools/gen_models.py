# beautalks - radio programming software
# Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.
#
# Regenerates models/*.ini from CHIRP constants transcribed below.
# Usage: python3 tools/gen_models.py models
import os, sys
OUT = sys.argv[1]
HDR = "; beautalks - radio programming software\n; Copyright (C) 2026 Anaxarchus. Licensed under the GNU GPL v3 or later.\n; Model definition derived from CHIRP (GPLv3): %s\n"
SYM = "!@#$%^&*()+-=[]:\";'<>?,./"
UPPER_NUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ 1234567890"
ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz 1234567890"
ASCII = "".join(chr(x) for x in range(0x20, 0x7f))

SEND_STD = "hex:53454E4421050D010101041108050D0D01110F091209100400/1"
SEND_5RMPLUS = "hex:53454E44130F0D130E0E0E0D0A0E0E020F0804110C000D0E00/1"
SEND_F8HPPRO = "hex:53454E44120D0A0A10030D02110C120A110604" + "0E02090D0000/1"
def hx(s): return "hex:" + s.encode().hex().upper()
KEYS = [b"BHT ", b"CO 7", b"A ES", b" EIY", b"M PQ", b"XN Y", b"RVB ", b" HQP", b"W RC", b"MS N",
        b" SAT", b"K DH", b"ZO R", b"C SL", b"6RB ", b" JCG", b"PN V", b"J PK", b"EK L", b"I LZ"]
def key(i): return "hex:" + KEYS[i].hex().upper()

UV17_CH = dict(start="0", stride="32", empty_at="0", empty_byte="0xFF",
               blank="hex:" + "00"*16 + "FF"*16,
               rx="0 lbcd 4", tx="4 lbcd 4", rx_tone="8 tone_bf", tx_tone="10 tone_bf",
               power="14 bits 0 2", narrow="15 bits 6 1", bcl="15 bits 3 1", scan="15 bits 2 1",
               name="20 text 12")
UV5R_CH = dict(start="8", stride="16", first="0", count="128", empty_at="0", empty_byte="0xFF",
               blank="hex:" + "00"*16,
               rx="0 lbcd 4", tx="4 lbcd 4", rx_tone="8 tone_bf", tx_tone="10 tone_bf",
               power="14 bits 0 2", wide="15 bits 6 1", bcl="15 bits 3 1", scan="15 bits 2 1",
               name="0 text 7 table 0x1008 16")

AIR = "108-135.999999"
def uv17(fid, name, cls, *, vendor="Baofeng", aliases="", tested="untested", ident="PROGRAMBFNORMALU",
         magics=None, keyi=1, regions="0x0000+0x8040 0x9000+0x0040 0xA000+0x02C0 0xD000+0x0040",
         count=1000, powers="High, Low", watts="5, 1", rx_bands=None, am=False, airband=AIR,
         model_reply="", notes="", tx_bands=None):
    if magics is None:
        magics = "hex:46/16 hex:4D/15 " + SEND_STD
    if rx_bands is None:
        rx_bands = "136-174 200-260 400-520"
    if tx_bands is None:
        tx_bands = " ".join(b for b in rx_bands.split() if not b.startswith("108"))
    ch = dict(UV17_CH); ch.update(count=str(count), first="1")
    ch.update(powers=powers, watts=watts, rx_bands=rx_bands, tx_bands=tx_bands,
              modes="FM,NFM,AM" if am else "FM,NFM", charset=ALNUM + SYM)
    if am:
        ch["am_bands"] = airband
    write(fid, cls, dict(vendor=vendor, name=name, aliases=aliases, engine="uv17pro", tested=tested,
                          source="CHIRP baofeng_uv17Pro.py class " + cls, notes=notes),
          dict(baud="115200", ident=ident, magics=magics, key=key(keyi) if keyi is not None else "none",
               block="0x40", regions=regions),
          dict(model_reply=model_reply, ident_reply=""), ch)

M_ORIG = "hex:50BBFF0125984D"; M_291 = "hex:50BBFF20120725"; M_F11 = "hex:50BBFF13A111DD"
M_UV82 = "hex:50BBFF20130105"; M_UV6 = "hex:50BBFF20120823"; M_UV6O = "hex:50BBFF1203984D"
M_A58 = "hex:50BBFF20140413"; M_UV5G = "hex:50BBFF20120625"
BT_UV5R = "BFS BFB N5R-2 N5R2 N5RV BTS D5R2 B5R2"
def uv5r(fid, name, cls, *, vendor="Baofeng", aliases="", tested="untested", magics=(M_291, M_ORIG),
         aux="yes", orig="bfb", basetype=BT_UV5R, tri=False, bands="130-176 220-260 400-520",
         charset=UPPER_NUM + SYM, first="0", ident_reply="", notes="", modes="FM,NFM", am_bands="", tx_bands=""):
    ch = dict(UV5R_CH); ch["first"] = first
    if tri:
        ch.update(powers="High, Med, Low", watts="8, 4, 1")
    else:
        ch.update(powers="High, Low", watts="4, 1")
    ch.update(rx_bands=bands, tx_bands=tx_bands or " ".join(b for b in bands.split() if not b.startswith("108")),
              modes=modes, charset=charset)
    if am_bands:
        ch["am_bands"] = am_bands
    write(fid, cls, dict(vendor=vendor, name=name, aliases=aliases, engine="uv5r", tested=tested,
                          source="CHIRP uv5r.py class " + cls, notes=notes),
          dict(baud="9600", magics=" ".join(magics), aux=aux, orig_check=orig, basetype=basetype,
               block="0x40"),
          dict(model_reply="", ident_reply=ident_reply), ch)

def val(v):
    return v

def write(fid, cls, model, link, detect, ch):
    p = os.path.join(OUT, fid + ".ini")
    with open(p, "w") as f:
        f.write(HDR % ("class " + cls))
        for sec, d in (("model", model), ("link", link), ("detect", detect), ("channels", ch)):
            f.write("\n[%s]\n" % sec)
            for k, v in d.items():
                f.write("%s = %s\n" % (k, val(v)) if v != "" else "%s =\n" % k)

# ---------------- UV-17Pro family ----------------
FIVE = "108-135.999999 136-174 200-260 350-390 400-520"
uv17("uv-5rm", "UV-5RM", "BF5RM", aliases="5RM, BF-5RM", tested="write",
     powers="High, Low, Medium", watts="8, 1, 5", rx_bands=FIVE, am=True, model_reply="5RH",
     notes="Download and full safe write (backup, 526-block write, verify) confirmed on hardware 2026-11-08 (M reply '5RH     +L00000').")
uv17("uv-17pro", "UV-17Pro", "UV17Pro")
uv17("uv-21prov2", "UV-21ProV2", "UV21ProV2", am=True,
     rx_bands="108-135.999999 136-174 220-260 350-390 400-479.999999 480-520",
     tx_bands="136-174 220-260 400-479.999999")
uv17("uv-25", "UV-25", "UV25")
uv17("uv-17progps", "UV-17ProGPS", "UV17ProGPS", ident="PROGRAMCOLORPROU",
     magics="hex:46/16 hex:4D/7 " + SEND_STD, rx_bands=FIVE, am=True)
for fid, nm, cl, vend in (("gm-30-plus", "GM-30 Plus", "RadioddityGM30Plus", "Radioddity"),
                          ("gm-30-pro", "GM-30 Pro", "RadioddityGM30Pro", "Radioddity"),
                          ("gm-21", "GM-21", "BaofengGM21", "Baofeng")):
    uv17(fid, nm, cl, vendor=vend, ident="PROGRAMCOLORPROU", magics="hex:46/16 hex:4D/7 " + SEND_STD,
         rx_bands=FIVE, am=True,
         notes="CHIRP (UV17ProGPSGMRS) also forces NFM/low power on 467 MHz interstitials in software; "
               "beautalks does not police frequencies.")
uv17("uv-32", "UV-32", "UV32", ident="PROGRAMCOLORPROU", magics="hex:46/16 hex:4D/7 " + SEND_STD,
     rx_bands=FIVE, am=True, powers="High, Low, Medium", watts="10, 2, 5")
uv17("uv-21progps", "UV-21ProGPS", "UV21ProGPS", ident="PROGRAMCOLORPROU",
     magics="hex:46/16 hex:4D/7 " + SEND_STD, am=True,
     rx_bands="108-135.999999 136-174 220-260 350-390 400-479.999999 480-520",
     tx_bands="136-174 220-260 400-479.999999")
uv17("uv-28plus", "UV-28Plus", "UV28Plus", ident="PROGRAMCOLORPROU",
     magics="hex:46/16 hex:4D/7 " + SEND_STD, am=True, powers="High, Low, Medium", watts="10, 2, 5",
     rx_bands="108-135.999999 136-174 220-260 350-390 400-479.999999 480-520",
     tx_bands="136-174 220-260 400-479.999999")
uv17("maxtalker-p15", "P15", "MaxTalkerP15", vendor="MaxTalker",
     powers="High, Low, Medium", watts="8, 1, 5", rx_bands=FIVE, am=True)
uv17("maxtalker-mt-5rm", "MT-5RM", "MaxTalkerMT5RM", vendor="MaxTalker",
     powers="High, Low, Medium", watts="8, 1, 5", rx_bands=FIVE, am=True)
uv17("k5-plus", "K5-Plus", "BFK5Plus", powers="High, Low, Medium", watts="8, 1, 5", rx_bands=FIVE, am=True)
uv17("uv-5rm-plus", "UV-5RM Plus", "BaofengUV5RMPlus", powers="High, Low, Medium", watts="8, 1, 5",
     rx_bands=FIVE, am=True, keyi=13, magics="hex:46/16 hex:4D/15 " + SEND_5RMPLUS)
uv17("gm-5rh", "GM-5RH", "GM5RH", ident="PROGRAMBFGMRS05U", powers="High, Low, Medium", watts="5, 0.5, 3")
uv17("uv-5g-plus", "UV-5G Plus", "UV5GPlus", vendor="Radioddity", ident="PROGRAMBFGMRS05U",
     powers="High, Low, Medium", watts="5, 0.5, 3")
uv17("uv-17r-plus", "UV-17R-Plus", "UV17RPlus", rx_bands=FIVE, am=True)
uv17("uv-5rh", "UV-5RH", "UV5RH", powers="High, Low, Medium", watts="10, 2, 5", rx_bands=FIVE, am=True)
uv17("bf-f8hp-pro", "BF-F8HP-PRO", "F8HPPro", ident="PROGRAMBF5RTECHU",
     magics="hex:46/16 hex:4D/6 " + SEND_F8HPPRO, keyi=3,
     regions="0x0000+0x8040 0x9000+0x0080 0xA000+0x02C0 0xD000+0x00C0",
     powers="High, Low, Mid", watts="10, 1, 3", am=True,
     rx_bands="108-136.999999 137-173.999999 174-218.999999 219-224.999999 225-399.999999 400-520",
     tx_bands="137-173.999999 219-224.999999 400-520",
     airband="108-136.999999 174-218.999999 225-399.999999")
uv17("k6", "K6", "BFK6", ident="PROGRAMBF-K6PROU", magics="hex:46/16", keyi=None,
     regions="0x0000+0x8040 0x9000+0x0080 0xA000+0x02C0 0xC000+0x0040 0xD000+0x0040", count=999,
     rx_bands="108-135.999999 136-174 200-260 400-600 350-390", am=True)
uv17("uv-5r-mini", "UV-5R Mini", "UV5RMini", ident="PROGRAMCOLORPROU",
     regions="0x0000+0x8040 0x9000+0x0040 0xA000+0x01C0", count=999, am=True,
     rx_bands="108-135.999999 136-174 350-390 400-480 480-520", tx_bands="136-174 400-480")
uv17("uv-5g-mini", "UV-5G Mini", "UV5GMini", notes="Channels 1-30 are fixed GMRS channels in the radio (CHIRP marks them immutable); beautalks does not yet stop edits there.", ident="PROGRAMGMRS5RMIU PROGRAMCOLORPROU",
     regions="0x0000+0x8040 0x9000+0x0040 0xA000+0x01C0", count=999, am=True,
     rx_bands="108-135.999999 136-174 350-390 400-480 480-520", tx_bands="136-174 400-480")

# ---------------- UV-5R family ----------------
uv5r("uv-5r", "UV-5R", "BaofengUV5R / BaofengUV5RGeneric", tested="write",
     aliases="UV-5RE, UV-5X, RT5R, RT5RV, RT5, RH5R, UV-5R EX, A-5R, BaofengUV5R",
     notes="UV-5RE (firmware HN5RV011, BFB291+ magic): download and guarded safe write (backup, write, verify) confirmed on hardware 2026-11-08. Other firmware generations are untested.")
uv5r("uv-5g-pro", "UV-5G Pro", "BaofengUV5GPro", modes="FM,NFM,AM", am_bands="108-135.999999",
     bands="108-135.999999 136-174 220-260 350-390 400-520")
uv5r("f-11", "F-11", "BaofengF11Radio", magics=(M_F11,), orig="never", basetype="USA")
uv5r("uv-82", "UV-82", "BaofengUV82Radio", magics=(M_UV82,), orig="never",
     basetype="US2S2 B82S BF82 N82-2 N822", bands="130-176 220-260 400-521", charset=ASCII)
uv5r("uv-82x3", "UV-82X3", "Radioddity82X3Radio", vendor="Radioddity", magics=(M_UV82,), orig="never",
     basetype="HN5RV01", bands="130-176 200-260 400-521", charset=ASCII)
uv5r("uv-6", "UV-6", "BaofengUV6Radio", aliases="UV-7", magics=(M_UV6, M_UV6O), aux="no", orig="never",
     basetype="BF1 UV6", first="1")
uv5r("kt-980hp", "KT-980HP", "IntekKT980Radio", vendor="Intek", magics=(M_291,), orig="never",
     basetype="BFP3V3_B", tri=True, bands="130-180 220-260 400-521")
uv5r("bf-f8hp", "BF-F8HP", "BaofengBFF8HPRadio", magics=(M_291, M_A58), orig="never",
     basetype="BFP3V3_F N5R-3 N5R3 F5R3 BFT N5RV", tri=True, bands="130-180 220-260 400-521",
     aliases="RT5(tri-power), GA-5S, UV-5XP, TI-F8+, UV-5R Pro, TS-T9+, TD-UV5R TriPower")
uv5r("uv-82hp", "UV-82HP", "BaofengUV82HPRadio", magics=(M_UV82,), orig="never",
     basetype="N82-3 N823 N5R2", tri=True, bands="136-175 220-260 400-521", charset=ALNUM + SYM,
     aliases="UV-82 Pro")
uv5r("uv-5rx3", "UV-5RX3", "RadioddityUV5RX3Radio", vendor="Radioddity", bands="130-176 200-260 400-520")
uv5r("gt-5r", "GT-5R", "RadioddityGT5RRadio", tx_bands="144-147.999999 420-449.999999",
     notes="The GT-5R transmits only on 144-148 and 420-450 MHz (CHIRP vhftx/uhftx); receives the UV-5R bands.")
uv5r("uv-5g", "UV-5G", "RadioddityUV5GRadio", vendor="Radioddity", magics=(M_UV5G,))
