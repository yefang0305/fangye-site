(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ImgLogic = api;
})(typeof self !== 'undefined' ? self : this, function () {
  function fitContain(srcW, srcH, maxW, maxH) {
    const scale = Math.min(maxW / srcW, maxH / srcH, 1);
    return { width: Math.round(srcW * scale), height: Math.round(srcH * scale), scale };
  }
  function displayToImage(dx, dy, scale) {
    return { x: Math.floor(dx / scale), y: Math.floor(dy / scale) };
  }
  function imageToDisplay(ix, iy, scale) {
    return { x: ix * scale, y: iy * scale };
  }
  function computeResize(srcW, srcH, opt) {
    let scale;
    if (opt.mode === 'longEdge') scale = Math.min(opt.value / Math.max(srcW, srcH), 1);
    else if (opt.mode === 'percent') scale = opt.value / 100;
    else if (opt.mode === 'width') scale = opt.value / srcW;
    else throw new Error('unknown resize mode: ' + opt.mode);
    const width = Math.max(1, Math.round(srcW * scale));
    const height = Math.max(1, Math.round(srcH * scale));
    return { width, height };
  }
  async function qualitySearch({ measure, targetBytes, minQ = 0.3, maxQ = 0.95, iterations = 7 }) {
    let lo = minQ, hi = maxQ;
    let best = null;
    // 先测最低质量，作为兜底
    const loBytes = await measure(lo);
    if (loBytes > targetBytes) return { quality: lo, bytes: loBytes };
    best = { quality: lo, bytes: loBytes };
    for (let i = 0; i < iterations; i++) {
      const mid = (lo + hi) / 2;
      const bytes = await measure(mid);
      if (bytes <= targetBytes) { best = { quality: mid, bytes }; lo = mid; }
      else { hi = mid; }
    }
    return best;
  }

  function classifyCut(ix, iy, imgW, imgH, edgeRatio) {
    const er = edgeRatio == null ? 0.15 : edgeRatio;
    const distLR = Math.min(ix, imgW - ix);            // 离左右边缘距离
    const distTB = Math.min(iy, imgH - iy);            // 离上下边缘距离
    const nearLR = distLR <= er * imgW;
    const nearTB = distTB <= er * imgH;
    if (nearLR && (!nearTB || distLR / imgW <= distTB / imgH)) return { type: 'horizontal', pos: iy };
    if (nearTB) return { type: 'vertical', pos: ix };
    return null;
  }

  function equalCuts(length, n) {
    if (n <= 1) return [];
    const out = [];
    for (let i = 1; i < n; i++) out.push(Math.round((length * i) / n));
    return out;
  }

  function sliceRects(imgW, imgH, xs, ys) {
    const dedupSorted = (arr, max) => {
      const s = Array.from(new Set(arr.map(Math.round)))
        .filter((v) => v > 0 && v < max)
        .sort((a, b) => a - b);
      return s;
    };
    const xb = [0, ...dedupSorted(xs, imgW), imgW];
    const yb = [0, ...dedupSorted(ys, imgH), imgH];
    const rects = [];
    let index = 1;
    for (let r = 0; r < yb.length - 1; r++) {
      for (let c = 0; c < xb.length - 1; c++) {
        rects.push({ x: xb[c], y: yb[r], w: xb[c + 1] - xb[c], h: yb[r + 1] - yb[r], index: index++ });
      }
    }
    return rects;
  }

  function numberedName(index, ext) {
    return index + '.' + ext;
  }

  const CRC_TABLE = (function () {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      t[n] = c >>> 0;
    }
    return t;
  })();
  function crc32(bytes) {
    let c = 0xffffffff;
    for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }
  function zipStore(files) {
    const enc = new TextEncoder();
    const chunks = [];      // 本地文件头 + 数据
    const central = [];     // 中央目录
    let offset = 0;
    const u16 = (v) => [v & 0xff, (v >>> 8) & 0xff];
    const u32 = (v) => [v & 0xff, (v >>> 8) & 0xff, (v >>> 16) & 0xff, (v >>> 24) & 0xff];
    for (const f of files) {
      const nameBytes = enc.encode(f.name);
      const data = f.data;
      const crc = crc32(data);
      const local = [].concat(
        u32(0x04034b50), u16(20), u16(0), u16(0), u16(0), u16(0),
        u32(crc), u32(data.length), u32(data.length),
        u16(nameBytes.length), u16(0)
      );
      chunks.push(new Uint8Array(local), nameBytes, data);
      const localSize = local.length + nameBytes.length + data.length;
      const cd = [].concat(
        u32(0x02014b50), u16(20), u16(20), u16(0), u16(0), u16(0), u16(0),
        u32(crc), u32(data.length), u32(data.length),
        u16(nameBytes.length), u16(0), u16(0), u16(0), u16(0), u32(0),
        u32(offset)
      );
      central.push(new Uint8Array(cd), nameBytes);
      offset += localSize;
    }
    const cdStart = offset;
    let cdSize = 0;
    for (const c of central) cdSize += c.length;
    const eocd = new Uint8Array([].concat(
      u32(0x06054b50), u16(0), u16(0), u16(files.length), u16(files.length),
      u32(cdSize), u32(cdStart), u16(0)
    ));
    const all = chunks.concat(central, [eocd]);
    let total = 0;
    for (const c of all) total += c.length;
    const out = new Uint8Array(total);
    let p = 0;
    for (const c of all) { out.set(c, p); p += c.length; }
    return out;
  }

  return { fitContain, displayToImage, imageToDisplay, computeResize, qualitySearch, classifyCut, equalCuts, sliceRects, numberedName, crc32, zipStore };
});
