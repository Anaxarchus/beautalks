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

    identify() {
        this.link.discard();
        this.link.write(this.ident_bytes());
        let ack = __dados_from_any(this.link.read(1, 1000), ["[]", "byte"]);
        if (ack.length === 0) {
            throw __dados_raise(new __dados_Error("no answer to the program-mode string", this.NO_ANSWER, new __dados_Location("engines/uv17pro.dados", 112, 14, "main.Uv17pro.identify")));
        }
        if ((ack[0] ?? __dados_a_oob(ack, 0)) !== 6) {
            throw __dados_raise(new __dados_Error("program mode refused: " + __dados_str_int(ack[0] ?? __dados_a_oob(ack, 0)), this.BAD_REPLY, new __dados_Location("engines/uv17pro.dados", 114, 14, "main.Uv17pro.identify")));
        }
        let replies = "";
        for (let spec of this.words(__dados_m_get(this.model, "link.magics", ""))) {
            let parts = spec.split("/");
            if (parts.length !== 2) {
                throw __dados_raise(new __dados_Error(("bad magic '" + spec) + "'", this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 119, 18, "main.Uv17pro.identify")));
            }
            let label = (parts[0] ?? __dados_a_oob(parts, 0)).startsWith("hex:") ? __dados_s_slice(parts[0] ?? __dados_a_oob(parts, 0), 4, (parts[0] ?? __dados_a_oob(parts, 0)).length) : (parts[0] ?? __dados_a_oob(parts, 0));
            let magic = this.hex_bytes(parts[0] ?? __dados_a_oob(parts, 0));
            let want = this.number(parts[1] ?? __dados_a_oob(parts, 1));
            this.link.write(magic);
            let got = __dados_from_any(this.link.read(want, 1000), ["[]", "byte"]);
            if (got.length !== want) {
                throw __dados_raise(new __dados_Error(((((("magic " + label) + ": ") + __dados_str_int(got.length)) + " of ") + __dados_str_int(want)) + " bytes", this.NO_ANSWER, new __dados_Location("engines/uv17pro.dados", 126, 18, "main.Uv17pro.identify")));
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
                throw __dados_raise(new __dados_Error(("bad region '" + r) + "'", this.BAD_MODEL, new __dados_Location("engines/uv17pro.dados", 139, 18, "main.Uv17pro.regions")));
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
        this.identify();
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
                    throw __dados_raise(new __dados_Error(((("block " + __dados_str_int(addr)) + ": ") + __dados_str_int(got.length)) + " bytes", this.NO_ANSWER, new __dados_Location("engines/uv17pro.dados", 161, 22, "main.Uv17pro.download")));
                }
                if ((((got[0] ?? __dados_a_oob(got, 0)) !== 82) || ((got[1] ?? __dados_a_oob(got, 1)) !== __dados_int_and(addr >= -2147483648 && addr <= 2147483647 ? addr >> 8 : __dados_int_shr(addr, 8), 255))) || ((got[2] ?? __dados_a_oob(got, 2)) !== __dados_int_and(addr, 255))) {
                    throw __dados_raise(new __dados_Error(("block " + __dados_str_int(addr)) + ": bad header", this.BAD_REPLY, new __dados_Location("engines/uv17pro.dados", 163, 22, "main.Uv17pro.download")));
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
            throw __dados_raise(new __dados_Error((("image is " + __dados_str_int(image.length)) + " bytes, model wants ") + __dados_str_int(total), this.IMAGE_SIZE, new __dados_Location("engines/uv17pro.dados", 174, 14, "main.Uv17pro.upload")));
        }
        this.identify();
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
                    throw __dados_raise(new __dados_Error(("block " + __dados_str_int(addr)) + " not acknowledged", this.REFUSED, new __dados_Location("engines/uv17pro.dados", 187, 22, "main.Uv17pro.upload")));
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
__dados_lines("engines/uv17pro.dados", ["main.Uv17pro.init", "main.Uv17pro.api", "main.Uv17pro.hex_digit", "main.Uv17pro.hex_bytes", "main.Uv17pro.number", "main.Uv17pro.need", "main.Uv17pro.words", "main.Uv17pro.crypt", "main.Uv17pro.ident_bytes", "main.Uv17pro.identify", "main.Uv17pro.regions", "main.Uv17pro.total_size", "main.Uv17pro.download", "main.Uv17pro.upload"], [
    5, 0, 0, -1, 18, 31, 5, 0, 19, 32, 5, 0, 20, 0, 0, -1, 23, 36, 5, 1, 24, 0, 0, -1, 27, 41, 5, 2, 28, 42, 5, 2,
    29, 43, 5, 2, 30, 44, 9, 2, 31, 43, 5, 2, 32, 45, 5, 2, 33, 0, 0, -1, 36, 49, 5, 3, 37, 50, 5, 3, 38, 51, 9, 3,
    39, 50, 5, 3, 40, 52, 5, 3, 41, 53, 9, 3, 42, 52, 5, 3, 43, 54, 5, 3, 44, 55, 5, 3, 47, 56, 9, 3, 48, 55, 5, 3,
    50, 57, 5, 3, 51, 0, 0, -1, 54, 61, 5, 4, 55, 62, 5, 4, 56, 63, 9, 4, 57, 64, 9, 4, 60, 65, 13, 4, 61, 64, 9, 4,
    63, 66, 9, 4, 64, 62, 5, 4, 65, 67, 5, 4, 66, 0, 0, -1, 69, 70, 5, 5, 70, 71, 5, 5, 71, 72, 9, 5, 72, 71, 5, 5,
    73, 73, 5, 5, 74, 0, 0, -1, 77, 77, 5, 6, 78, 78, 5, 6, 79, 79, 9, 6, 80, 80, 13, 6, 81, 79, 9, 6, 82, 78, 5, 6,
    83, 81, 5, 6, 84, 0, 0, -1, 87, 86, 5, 7, 88, 87, 9, 7, 89, 86, 5, 7, 90, 88, 5, 7, 91, 89, 5, 7, 96, 90, 9, 7,
    97, 91, 9, 7, 98, 92, 13, 7, 99, 91, 9, 7, 100, 94, 13, 7, 101, 91, 9, 7, 102, 89, 5, 7, 104, 95, 5, 7, 105, 0, 0, -1,
    108, 100, 5, 8, 109, 101, 5, 8, 110, 102, 9, 8, 111, 101, 5, 8, 112, 103, 5, 8, 113, 0, 0, -1, 116, 108, 5, 9, 117, 109, 5, 9,
    118, 110, 5, 9, 119, 111, 5, 9, 120, 112, 9, 9, 121, 111, 5, 9, 122, 113, 5, 9, 123, 114, 9, 9, 124, 113, 5, 9, 125, 115, 5, 9,
    126, 116, 5, 9, 127, 117, 9, 9, 128, 118, 9, 9, 129, 119, 13, 9, 130, 118, 9, 9, 131, 120, 9, 9, 132, 121, 9, 9, 133, 122, 9, 9,
    134, 123, 9, 9, 135, 124, 9, 9, 136, 125, 9, 9, 137, 126, 13, 9, 138, 125, 9, 9, 139, 127, 9, 9, 140, 128, 13, 9, 141, 127, 9, 9,
    142, 130, 13, 9, 143, 127, 9, 9, 144, 116, 5, 9, 145, 131, 5, 9, 146, 0, 0, -1, 149, 135, 5, 10, 150, 136, 5, 10, 151, 137, 9, 10,
    152, 138, 9, 10, 153, 139, 13, 10, 154, 138, 9, 10, 155, 140, 9, 10, 156, 136, 5, 10, 157, 141, 5, 10, 158, 0, 0, -1, 161, 144, 5, 11,
    162, 145, 5, 11, 163, 146, 9, 11, 164, 145, 5, 11, 165, 147, 5, 11, 166, 0, 0, -1, 169, 150, 5, 12, 170, 151, 5, 12, 171, 152, 5, 12,
    172, 153, 5, 12, 173, 154, 5, 12, 174, 155, 5, 12, 175, 156, 9, 12, 176, 157, 9, 12, 177, 158, 13, 12, 178, 159, 13, 12, 179, 160, 13, 12,
    180, 161, 17, 12, 181, 160, 13, 12, 182, 162, 13, 12, 183, 163, 17, 12, 184, 162, 13, 12, 185, 164, 13, 12, 186, 165, 13, 12, 187, 166, 13, 12,
    188, 157, 9, 12, 189, 155, 5, 12, 190, 167, 5, 12, 191, 0, 0, -1, 194, 172, 5, 13, 195, 173, 5, 13, 196, 174, 9, 13, 197, 173, 5, 13,
    198, 175, 5, 13, 199, 176, 5, 13, 200, 177, 5, 13, 201, 178, 5, 13, 202, 179, 5, 13, 203, 180, 9, 13, 204, 181, 9, 13, 205, 182, 13, 13,
    206, 183, 13, 13, 207, 184, 13, 13, 208, 185, 13, 13, 209, 186, 13, 13, 210, 187, 17, 13, 211, 186, 13, 13, 212, 188, 13, 13, 213, 189, 13, 13,
    214, 190, 13, 13, 215, 181, 9, 13, 216, 179, 5, 13, 217, 0, 0, -1,
]);
