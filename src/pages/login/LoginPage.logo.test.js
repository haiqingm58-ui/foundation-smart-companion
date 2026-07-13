import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";


function readJpegSize(buffer) {
  let offset = 2;
  while (offset < buffer.length) {
    if (buffer[offset] !== 0xff) throw new Error("Invalid JPEG marker");
    const marker = buffer[offset + 1];
    const length = buffer.readUInt16BE(offset + 2);
    if (marker >= 0xc0 && marker <= 0xc3) {
      return {
        height: buffer.readUInt16BE(offset + 5),
        width: buffer.readUInt16BE(offset + 7),
      };
    }
    offset += 2 + length;
  }
  throw new Error("JPEG dimensions not found");
}


describe("college logo asset", () => {
  test("uses a square cropped asset and renders without scale compensation", () => {
    const logo = readFileSync(resolve(process.cwd(), "public/college-logo.jpg"));
    const css = readFileSync(resolve(process.cwd(), "src/pages/login/LoginPage.css"), "utf8");
    const dimensions = readJpegSize(logo);
    const imageRule = css.match(/\.collegeLogo img\s*\{([^}]*)\}/)?.[1] ?? "";

    expect(dimensions.width).toBe(dimensions.height);
    expect(imageRule).toMatch(/object-fit:\s*contain/);
    expect(imageRule).not.toMatch(/transform:/);
  });
});
