import Foundation
import CoreText
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

// render <fontpath> <out.png> <W> <H> <size> <x> <y> <text>
let a = CommandLine.arguments
guard a.count >= 9 else { FileHandle.standardError.write("usage\n".data(using:.utf8)!); exit(2) }
let fontPath = a[1], outPath = a[2]
let W = Int(a[3])!, H = Int(a[4])!, size = CGFloat(Double(a[5])!)
let x = CGFloat(Double(a[6])!), y = CGFloat(Double(a[7])!)
let text = a[8...].joined(separator: " ")

let url = URL(fileURLWithPath: fontPath) as CFURL
guard let provider = CGDataProvider(url: url), let cgFont = CGFont(provider) else { exit(3) }
let font = CTFontCreateWithGraphicsFont(cgFont, size, nil, nil)

let attrs: [CFString: Any] = [
    kCTFontAttributeName: font,
    kCTForegroundColorAttributeName: CGColor(srgbRed: 0, green: 0, blue: 0, alpha: 1)
]
let s = CFAttributedStringCreate(nil, text as CFString, attrs as CFDictionary)!
let line = CTLineCreateWithAttributedString(s)

let cs = CGColorSpaceCreateDeviceRGB()
let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0,
                    space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setFillColor(CGColor(srgbRed: 1, green: 1, blue: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: CGFloat(W), height: CGFloat(H)))
ctx.textPosition = CGPoint(x: x, y: CGFloat(H) - y)
CTLineDraw(line, ctx)
let img = ctx.makeImage()!
let dest = CGImageDestinationCreateWithURL(URL(fileURLWithPath: outPath) as CFURL, UTType.png.identifier as CFString, 1, nil)!
CGImageDestinationAddImage(dest, img, nil)
CGImageDestinationFinalize(dest)
print("wrote \(outPath)")
