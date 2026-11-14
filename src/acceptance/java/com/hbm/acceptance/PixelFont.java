package com.hbm.acceptance;

import com.mojang.blaze3d.platform.NativeImage;

import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/** A 3x5 pixel font for contact-sheet labels (the game's font renders through GL, not into a NativeImage). */
final class PixelFont {
    private static final Map<Character, String> GLYPHS = new HashMap<>();

    static {
        String[] defs = {
                "0111101101101111", "1010110010010111", "2111001111100111", "3111001111001111", "4101101111001001",
                "5111100111001111", "6111100111101111", "7111001001001001", "8111101111101111", "9111101111001111",
                "A010101111101101", "B110101110101110", "C011100100100011", "D110101101101110", "E111100110100111",
                "F111100110100100", "G011100101101011", "H101101111101101", "I111010010010111", "J001001001101010",
                "K101101110101101", "L100100100100111", "M101111111101101", "N110101101101101", "O010101101101010",
                "P110101110100100", "Q010101101110011", "R110101110101101", "S011100010001110", "T111010010010010",
                "U101101101101111", "V101101101101010", "W101101111111101", "X101101010101101", "Y101101010010010",
                "Z111001010100111", "=000111000111000", "-000000111000000", "_000000000000111", ":000010000010000",
                "/001001010100100", ".000000000000010", " 000000000000000", "+000010111010000", ",000000000010100",
        };
        for (String d : defs) GLYPHS.put(d.charAt(0), d.substring(1));
    }

    private PixelFont() {
    }

    /** Draws {@code text} (upper-cased; unknown characters as '.') on a black bar, clipped at {@code maxWidth} pixels. */
    static void draw(NativeImage image, int x, int y, String text, int abgr, int scale, int maxWidth) {
        String t = text.toUpperCase(Locale.ROOT);
        int advance = 4 * scale;
        int width = Math.min(maxWidth, t.length() * advance);
        for (int py = y - 1; py < y + 5 * scale + 1 && py < image.getHeight(); py++)
            for (int px = x - 1; px < x + width + 1 && px < image.getWidth(); px++)
                if (px >= 0 && py >= 0) image.setPixelRGBA(px, py, 0xFF000000);
        for (int i = 0; i < t.length(); i++) {
            int cx = x + i * advance;
            if (cx + 3 * scale > x + maxWidth) break;
            String g = GLYPHS.getOrDefault(t.charAt(i), GLYPHS.get('.'));
            for (int row = 0; row < 5; row++)
                for (int col = 0; col < 3; col++) {
                    if (g.charAt(row * 3 + col) != '1') continue;
                    for (int sy = 0; sy < scale; sy++)
                        for (int sx = 0; sx < scale; sx++) {
                            int px = cx + col * scale + sx, py = y + row * scale + sy;
                            if (px < image.getWidth() && py < image.getHeight()) image.setPixelRGBA(px, py, abgr);
                        }
                }
        }
    }
}
