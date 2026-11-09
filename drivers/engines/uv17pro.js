// module "main/Uv17pro": the DadoScript class `Uv17pro` of package `main`, emitted by dadoc.
// Embedded in C as `dado_js__main__Uv17pro`, named by `dado_jsname__main__Uv17pro`.
import { __dados_Error, __dados_Location, __dados_a_append_array, __dados_a_decode_utf8, __dados_a_oob, __dados_a_slice, __dados_byte, __dados_from_any, __dados_int_add, __dados_int_and, __dados_int_div, __dados_int_mod, __dados_int_mul, __dados_int_shr, __dados_int_xor, __dados_lines, __dados_m_get, __dados_raise, __dados_s_bytes, __dados_s_index_of, __dados_s_oob, __dados_s_slice, __dados_s_to_int, __dados_str_any, __dados_str_int, __dados_str_map, __dados_str_string } from "dados:runtime";

export class Uv17pro {
    constructor(l, m) {
        this.link = 0;
        this.model = new Map();
        this.NO_ANSWER = 2;
        this.BAD_REPLY = 3;
        this.REFUSED = 4;
        this.BAD_MODEL = 7;
        this.IMAGE_SIZE = 8;
        this.init(l, m);
    }

    init(l, m) {
        this.link = l;
        this.model = m;
    }

    api() {
        return 1;
    }

    hex_digit(c) {
        let digits = "0123456789abcdef";
        let lc = c.toLowerCase();
        if ((!digits.includes(lc)) || (lc.length !== 1)) {
            throw __dados_raise(new __dados_Error(("bad hex digit '" + c) + "'", this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 44, 14, "main.Uv17pro.hex_digit")));
        }
        return __dados_s_index_of(digits, lc);
    }

    hex_bytes(spec) {
        let h = spec.trim();
        if (h.startsWith("hex:")) {
            h = __dados_s_slice(h, 4, h.length);
        }
        if (__dados_int_mod(h.length, 2) !== 0) {
            throw __dados_raise(new __dados_Error(("odd-length hex '" + spec) + "'", this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 53, 14, "main.Uv17pro.hex_bytes")));
        }
        let out = [];
        {
            const end$1 = __dados_int_div(h.length, 2);
            for (let i = 0; i < end$1; i = __dados_int_add(i, 1)) {
                out.push(__dados_byte(__dados_int_add(__dados_int_mul(this.hex_digit(h[__dados_int_mul(2, i)] ?? __dados_s_oob(h, __dados_int_mul(2, i))), 16), this.hex_digit(h[__dados_int_add(__dados_int_mul(2, i), 1)] ?? __dados_s_oob(h, __dados_int_add(__dados_int_mul(2, i), 1))))));
            }
        }
        return out;
    }

    number(text) {
        let t = text.trim().toLowerCase();
        if (t.startsWith("0x")) {
            let v = 0;
            {
                const end$2 = t.length;
                for (let i = 2; i < end$2; i = __dados_int_add(i, 1)) {
                    v = __dados_int_add(__dados_int_mul(v, 16), this.hex_digit(t[i] ?? __dados_s_oob(t, i)));
                }
            }
            return v;
        }
        return __dados_s_to_int(t);
    }

    need(key) {
        let v = __dados_m_get(this.model, key, "");
        if (v.trim().length === 0) {
            throw __dados_raise(new __dados_Error("model definition lacks " + key, this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 72, 14, "main.Uv17pro.need")));
        }
        return v.trim();
    }

    words(list) {
        let out = [];
        for (let w of list.split(" ")) {
            if (!(w.trim().length === 0)) {
                out.push(w.trim());
            }
        }
        return out;
    }

    crypt(key, data) {
        if (key.length === 0) {
            return data.slice();
        }
        let out = [];
        {
            const of$4 = data;
            for (let at$4 = 0; at$4 < of$4.length; at$4++) {
                let b = of$4[at$4];
                let i = at$4;
                let k = key[__dados_int_mod(i, 4)] ?? __dados_a_oob(key, __dados_int_mod(i, 4));
                if (((((k !== 32) && (b !== 0)) && (b !== 255)) && (b !== k)) && (b !== __dados_int_xor(k, 255))) {
                    out.push(__dados_byte(__dados_int_xor(b, k)));
                } else {
                    out.push(__dados_byte(b));
                }
            }
        }
        return out;
    }

    ident_bytes() {
        let id = this.need("link.ident");
        if (id.startsWith("hex:")) {
            return this.hex_bytes(id);
        }
        return __dados_s_bytes(id);
    }

    drain(quiet_ms) {
        {
            const end$5 = 40;
            for (let i = 0; i < end$5; i = __dados_int_add(i, 1)) {
                let junk = __dados_from_any(this.link.read(256, quiet_ms), ["[]", "byte"]);
                if (junk.length === 0) {
                    return;
                }
            }
        }
    }

    probe_once() {
        this.link.discard();
        this.link.write([82, 0, 0, 64]);
        let got = __dados_from_any(this.link.read(68, 600), ["[]", "byte"]);
        if (got.length === 0) {
            return 0;
        }
        if (((((got.length === 68) && ((got[0] ?? __dados_a_oob(got, 0)) === 82)) && ((got[1] ?? __dados_a_oob(got, 1)) === 0)) && ((got[2] ?? __dados_a_oob(got, 2)) === 0)) && ((got[3] ?? __dados_a_oob(got, 3)) === 64)) {
            this.drain(100);
            return 1;
        }
        return -1;
    }

    session_open() {
        let r = this.probe_once();
        if (r < 0) {
            this.drain(300);
            r = this.probe_once();
            if (r < 0) {
                this.drain(300);
            }
        }
        return r === 1;
    }

    identify() {
        let ack = [];
        {
            const end$6 = 3;
            for (let tries = 0; tries < end$6; tries = __dados_int_add(tries, 1)) {
                if (tries > 0) {
                    this.link.discard();
                    this.link.sleep(500);
                }
                this.link.discard();
                this.link.write(this.ident_bytes());
                ack = __dados_from_any(this.link.read(1, 1000), ["[]", "byte"]);
                if ((ack.length === 1) && ((ack[0] ?? __dados_a_oob(ack, 0)) === 6)) {
                    break;
                }
                if (ack.length === 1) {
                    this.drain(300);
                    if (this.session_open()) {
                        return "session";
                    }
                }
            }
        }
        if (ack.length === 0) {
            throw __dados_raise(new __dados_Error("no answer to the program-mode string", this.NO_ANSWER, new __dados_Location("engines/uv17pro.dados", 161, 14, "main.Uv17pro.identify")));
        }
        if ((ack[0] ?? __dados_a_oob(ack, 0)) !== 6) {
            throw __dados_raise(new __dados_Error("program mode refused: " + __dados_str_int(ack[0] ?? __dados_a_oob(ack, 0)), this.BAD_REPLY, new __dados_Location("engines/uv17pro.dados", 163, 14, "main.Uv17pro.identify")));
        }
        let replies = "";
        for (let spec of this.words(__dados_m_get(this.model, "link.magics", ""))) {
            let parts = spec.split("/");
            if (parts.length !== 2) {
                throw __dados_raise(new __dados_Error(("bad magic '" + spec) + "'", this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 168, 18, "main.Uv17pro.identify")));
            }
            let label = (parts[0] ?? __dados_a_oob(parts, 0)).startsWith("hex:") ? __dados_s_slice(parts[0] ?? __dados_a_oob(parts, 0), 4, (parts[0] ?? __dados_a_oob(parts, 0)).length) : (parts[0] ?? __dados_a_oob(parts, 0));
            let magic = this.hex_bytes(parts[0] ?? __dados_a_oob(parts, 0));
            let want = this.number(parts[1] ?? __dados_a_oob(parts, 1));
            this.link.write(magic);
            let got = __dados_from_any(this.link.read(want, 1000), ["[]", "byte"]);
            if (got.length !== want) {
                throw __dados_raise(new __dados_Error(((((("magic " + label) + ": ") + __dados_str_int(got.length)) + " of ") + __dados_str_int(want)) + " bytes", this.NO_ANSWER, new __dados_Location("engines/uv17pro.dados", 175, 18, "main.Uv17pro.identify")));
            }
            if ((magic.length === 1) && ((magic[0] ?? __dados_a_oob(magic, 0)) === 77)) {
                replies = ((replies + "M:") + __dados_a_decode_utf8(got)) + "\n";
            } else {
                replies = (((replies + label) + ":") + __dados_str_int(got.length)) + "\n";
            }
        }
        return replies;
    }

    regions() {
        let out = [];
        for (let r of this.words(this.need("link.regions"))) {
            let p = r.split("+");
            if (p.length !== 2) {
                throw __dados_raise(new __dados_Error(("bad region '" + r) + "'", this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 188, 18, "main.Uv17pro.regions")));
            }
            out.push([this.number(p[0] ?? __dados_a_oob(p, 0)), this.number(p[1] ?? __dados_a_oob(p, 1))]);
        }
        return out;
    }

    total_size() {
        let n = 0;
        for (let r of this.regions()) {
            n = __dados_int_add(n, r[1] ?? __dados_a_oob(r, 1));
        }
        return n;
    }

    download() {
        if (!this.session_open()) {
            this.identify();
        }
        let key = this.hex_bytes(__dados_m_get(this.model, "link.key", ""));
        let block = this.number(__dados_m_get(this.model, "link.block", "0x40"));
        let total = this.total_size();
        let image = [];
        for (let r of this.regions()) {
            let addr = r[0] ?? __dados_a_oob(r, 0);
            while (addr < __dados_int_add(r[0] ?? __dados_a_oob(r, 0), r[1] ?? __dados_a_oob(r, 1))) {
                this.link.write([82, __dados_int_and(addr >= -2147483648 && addr <= 2147483647 ? addr >> 8 : __dados_int_shr(addr, 8), 255), __dados_int_and(addr, 255), block]);
                let got = __dados_from_any(this.link.read(__dados_int_add(block, 4), 1000), ["[]", "byte"]);
                if (got.length !== __dados_int_add(block, 4)) {
                    throw __dados_raise(new __dados_Error(((("block " + __dados_str_int(addr)) + ": ") + __dados_str_int(got.length)) + " bytes", this.NO_ANSWER, new __dados_Location("engines/uv17pro.dados", 211, 22, "main.Uv17pro.download")));
                }
                if ((((got[0] ?? __dados_a_oob(got, 0)) !== 82) || ((got[1] ?? __dados_a_oob(got, 1)) !== __dados_int_and(addr >= -2147483648 && addr <= 2147483647 ? addr >> 8 : __dados_int_shr(addr, 8), 255))) || ((got[2] ?? __dados_a_oob(got, 2)) !== __dados_int_and(addr, 255))) {
                    throw __dados_raise(new __dados_Error(("block " + __dados_str_int(addr)) + ": bad header", this.BAD_REPLY, new __dados_Location("engines/uv17pro.dados", 213, 22, "main.Uv17pro.download")));
                }
                __dados_a_append_array(image, this.crypt(key, __dados_a_slice(got, 4, got.length)));
                addr = __dados_int_add(addr, block);
                this.link.progress(image.length, total);
            }
        }
        return image;
    }

    upload(image) {
        let total = this.total_size();
        if (image.length !== total) {
            throw __dados_raise(new __dados_Error((("image is " + __dados_str_int(image.length)) + " bytes, model wants ") + __dados_str_int(total), this.IMAGE_SIZE, new __dados_Location("engines/uv17pro.dados", 224, 14, "main.Uv17pro.upload")));
        }
        if (!this.session_open()) {
            this.identify();
        }
        let key = this.hex_bytes(__dados_m_get(this.model, "link.key", ""));
        let block = this.number(__dados_m_get(this.model, "link.block", "0x40"));
        let at = 0;
        for (let r of this.regions()) {
            let addr = r[0] ?? __dados_a_oob(r, 0);
            while (addr < __dados_int_add(r[0] ?? __dados_a_oob(r, 0), r[1] ?? __dados_a_oob(r, 1))) {
                let frame = [87, __dados_byte(__dados_int_and(addr >= -2147483648 && addr <= 2147483647 ? addr >> 8 : __dados_int_shr(addr, 8), 255)), __dados_byte(__dados_int_and(addr, 255)), __dados_byte(block)];
                __dados_a_append_array(frame, this.crypt(key, __dados_a_slice(image, at, __dados_int_add(at, block))));
                this.link.write(frame);
                let ack = __dados_from_any(this.link.read(1, 1000), ["[]", "byte"]);
                if ((ack.length !== 1) || ((ack[0] ?? __dados_a_oob(ack, 0)) !== 6)) {
                    throw __dados_raise(new __dados_Error(("block " + __dados_str_int(addr)) + " not acknowledged", this.REFUSED, new __dados_Location("engines/uv17pro.dados", 238, 22, "main.Uv17pro.upload")));
                }
                addr = __dados_int_add(addr, block);
                at = __dados_int_add(at, block);
                this.link.progress(at, total);
            }
        }
    }

    $name() {
        return "Uv17pro";
    }

    $parts() {
        return [__dados_str_any(this.link), __dados_str_map(this.model, __dados_str_string, __dados_str_string), __dados_str_int(this.NO_ANSWER), __dados_str_int(this.BAD_REPLY), __dados_str_int(this.REFUSED), __dados_str_int(this.BAD_MODEL), __dados_str_int(this.IMAGE_SIZE)];
    }
}

// Where each line above was written in `engines/uv17pro.dados`, for a trace.
__dados_lines("engines/uv17pro.dados", ["main.Uv17pro.init", "main.Uv17pro.api", "main.Uv17pro.hex_digit", "main.Uv17pro.hex_bytes", "main.Uv17pro.number", "main.Uv17pro.need", "main.Uv17pro.words", "main.Uv17pro.crypt", "main.Uv17pro.ident_bytes", "main.Uv17pro.drain", "main.Uv17pro.probe_once", "main.Uv17pro.session_open", "main.Uv17pro.identify", "main.Uv17pro.regions", "main.Uv17pro.total_size", "main.Uv17pro.download", "main.Uv17pro.upload"], [
    5, 0, 0, -1, 18, 31, 5, 0, 19, 32, 5, 0, 20, 0, 0, -1, 23, 36, 5, 1, 24, 0, 0, -1, 27, 41, 5, 2, 28, 42, 5, 2,
    29, 43, 5, 2, 30, 44, 9, 2, 31, 43, 5, 2, 32, 45, 5, 2, 33, 0, 0, -1, 36, 49, 5, 3, 37, 50, 5, 3, 38, 51, 9, 3,
    39, 50, 5, 3, 40, 52, 5, 3, 41, 53, 9, 3, 42, 52, 5, 3, 43, 54, 5, 3, 44, 55, 5, 3, 47, 56, 9, 3, 48, 55, 5, 3,
    50, 57, 5, 3, 51, 0, 0, -1, 54, 61, 5, 4, 55, 62, 5, 4, 56, 63, 9, 4, 57, 64, 9, 4, 60, 65, 13, 4, 61, 64, 9, 4,
    63, 66, 9, 4, 64, 62, 5, 4, 65, 67, 5, 4, 66, 0, 0, -1, 69, 70, 5, 5, 70, 71, 5, 5, 71, 72, 9, 5, 72, 71, 5, 5,
    73, 73, 5, 5, 74, 0, 0, -1, 77, 77, 5, 6, 78, 78, 5, 6, 79, 79, 9, 6, 80, 80, 13, 6, 81, 79, 9, 6, 82, 78, 5, 6,
    83, 81, 5, 6, 84, 0, 0, -1, 87, 86, 5, 7, 88, 87, 9, 7, 89, 86, 5, 7, 90, 88, 5, 7, 91, 89, 5, 7, 96, 90, 9, 7,
    97, 91, 9, 7, 98, 92, 13, 7, 99, 91, 9, 7, 100, 94, 13, 7, 101, 91, 9, 7, 102, 89, 5, 7, 104, 95, 5, 7, 105, 0, 0, -1,
    108, 100, 5, 8, 109, 101, 5, 8, 110, 102, 9, 8, 111, 101, 5, 8, 112, 103, 5, 8, 113, 0, 0, -1, 116, 112, 5, 9, 119, 113, 9, 9,
    120, 114, 9, 9, 121, 115, 13, 9, 122, 114, 9, 9, 123, 112, 5, 9, 125, 0, 0, -1, 128, 119, 5, 10, 129, 120, 5, 10, 130, 121, 5, 10,
    131, 122, 5, 10, 132, 123, 9, 10, 133, 122, 5, 10, 134, 124, 5, 10, 135, 125, 9, 10, 136, 126, 9, 10, 137, 124, 5, 10, 138, 127, 5, 10,
    139, 0, 0, -1, 142, 130, 5, 11, 143, 131, 5, 11, 144, 132, 9, 11, 145, 133, 9, 11, 146, 134, 9, 11, 147, 135, 13, 11, 148, 134, 9, 11,
    149, 131, 5, 11, 150, 136, 5, 11, 151, 0, 0, -1, 154, 143, 5, 12, 155, 144, 5, 12, 158, 145, 9, 12, 159, 146, 13, 12, 160, 147, 13, 12,
    161, 145, 9, 12, 162, 148, 9, 12, 163, 149, 9, 12, 164, 150, 9, 12, 165, 151, 9, 12, 166, 152, 13, 12, 167, 151, 9, 12, 168, 153, 9, 12,
    169, 156, 13, 12, 170, 157, 13, 12, 171, 158, 17, 12, 172, 157, 13, 12, 173, 153, 9, 12, 174, 144, 5, 12, 176, 160, 5, 12, 177, 161, 9, 12,
    178, 160, 5, 12, 179, 162, 5, 12, 180, 163, 9, 12, 181, 162, 5, 12, 182, 164, 5, 12, 183, 165, 5, 12, 184, 166, 9, 12, 185, 167, 9, 12,
    186, 168, 13, 12, 187, 167, 9, 12, 188, 169, 9, 12, 189, 170, 9, 12, 190, 171, 9, 12, 191, 172, 9, 12, 192, 173, 9, 12, 193, 174, 9, 12,
    194, 175, 13, 12, 195, 174, 9, 12, 196, 176, 9, 12, 197, 177, 13, 12, 198, 176, 9, 12, 199, 179, 13, 12, 200, 176, 9, 12, 201, 165, 5, 12,
    202, 180, 5, 12, 203, 0, 0, -1, 206, 184, 5, 13, 207, 185, 5, 13, 208, 186, 9, 13, 209, 187, 9, 13, 210, 188, 13, 13, 211, 187, 9, 13,
    212, 189, 9, 13, 213, 185, 5, 13, 214, 190, 5, 13, 215, 0, 0, -1, 218, 193, 5, 14, 219, 194, 5, 14, 220, 195, 9, 14, 221, 194, 5, 14,
    222, 196, 5, 14, 223, 0, 0, -1, 226, 199, 5, 15, 227, 200, 9, 15, 228, 199, 5, 15, 229, 201, 5, 15, 230, 202, 5, 15, 231, 203, 5, 15,
    232, 204, 5, 15, 233, 205, 5, 15, 234, 206, 9, 15, 235, 207, 9, 15, 236, 208, 13, 15, 237, 209, 13, 15, 238, 210, 13, 15, 239, 211, 17, 15,
    240, 210, 13, 15, 241, 212, 13, 15, 242, 213, 17, 15, 243, 212, 13, 15, 244, 214, 13, 15, 245, 215, 13, 15, 246, 216, 13, 15, 247, 207, 9, 15,
    248, 205, 5, 15, 249, 217, 5, 15, 250, 0, 0, -1, 253, 222, 5, 16, 254, 223, 5, 16, 255, 224, 9, 16, 256, 223, 5, 16, 257, 225, 5, 16,
    258, 226, 9, 16, 259, 225, 5, 16, 260, 227, 5, 16, 261, 228, 5, 16, 262, 229, 5, 16, 263, 230, 5, 16, 264, 231, 9, 16, 265, 232, 9, 16,
    266, 233, 13, 16, 267, 234, 13, 16, 268, 235, 13, 16, 269, 236, 13, 16, 270, 237, 13, 16, 271, 238, 17, 16, 272, 237, 13, 16, 273, 239, 13, 16,
    274, 240, 13, 16, 275, 241, 13, 16, 276, 232, 9, 16, 277, 230, 5, 16, 278, 0, 0, -1,
]);
