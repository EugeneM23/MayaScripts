"""Read a remote zip's directory and chosen members with HTTP range requests."""
import struct, urllib.request, zlib, json, sys, os
UA = {"User-Agent": "skeldar-gaitguide/1 (research; contact via repo)"}

def resolve(url):
    req = urllib.request.Request(url, headers=dict(UA, Range="bytes=0-0"))
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers["Content-Range"].split("/")[-1])
        return r.geturl(), total

def get(url, a, b):
    req = urllib.request.Request(url, headers=dict(UA, Range="bytes=%d-%d" % (a, b)))
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def directory(url, total):
    tail = get(url, max(0, total - 70000), total - 1)
    i = tail.rfind(b"PK\x05\x06")
    (_, disk, cd_disk, n_here, n, cd_size, cd_off, clen) = struct.unpack("<IHHHHIIH", tail[i:i + 22])
    if cd_off == 0xFFFFFFFF or n == 0xFFFF:
        j = tail.rfind(b"PK\x06\x06")
        n, cd_size, cd_off = struct.unpack("<QQQ", tail[j + 32:j + 56])
    cd = get(url, cd_off, cd_off + cd_size - 1)
    out, p = [], 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        (method, crc, csize, usize, nlen, xlen, mlen, lho) = struct.unpack("<6xH4xIIIHHH8xI", cd[p + 4:p + 46])
        name = cd[p + 46:p + 46 + nlen].decode("utf-8", "replace")
        extra = cd[p + 46 + nlen:p + 46 + nlen + xlen]
        if 0xFFFFFFFF in (csize, usize, lho):
            q = 0
            while q < len(extra):
                tag, ln = struct.unpack("<HH", extra[q:q + 4])
                if tag == 1:
                    vals = list(struct.unpack("<%dQ" % (ln // 8), extra[q + 4:q + 4 + ln]))
                    if usize == 0xFFFFFFFF: usize = vals.pop(0)
                    if csize == 0xFFFFFFFF: csize = vals.pop(0)
                    if lho == 0xFFFFFFFF: lho = vals.pop(0)
                q += 4 + ln
        out.append(dict(name=name, method=method, csize=csize, usize=usize, off=lho))
        p += 46 + nlen + xlen + mlen
    return out

def member(url, e):
    head = get(url, e["off"], e["off"] + 29)
    nlen, xlen = struct.unpack("<HH", head[26:30])
    start = e["off"] + 30 + nlen + xlen
    data = get(url, start, start + e["csize"] - 1) if e["csize"] else b""
    return zlib.decompress(data, -15) if e["method"] == 8 else data

if __name__ == "__main__":
    url, total = resolve(sys.argv[1])
    d = directory(url, total)
    json.dump(dict(url=url, total=total, entries=d), open(sys.argv[2], "w"))
    print(total, len(d))
