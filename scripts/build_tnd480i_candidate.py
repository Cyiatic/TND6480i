#!/usr/bin/env python3
import argparse
import hashlib
import json
import zlib
from pathlib import Path


GE_1172_OFFSET = 0x21990
CRC_BOOT_START = 0x1000
CRC_BOOT_END = 0x101000
CRC_6102_SEED = 0xF8CA4DDC


MAIN_RANGES = [
    (0x24B8, 0x2500, "display dimensions table"),
    (0x5CD4, 0x5D10, "VI table A"),
    (0x7594, 0x75D0, "VI table B"),
    (0x76F0, 0x7700, "dimension header only"),
    (0x9C3C, 0x9D24, "menu/display table A"),
    (0xA240, 0xA264, "menu/display table B"),
]


MAIN_RANGE_SETS = {
    "all": MAIN_RANGES,
    "core_no_menu": [
        (0x24B8, 0x2500, "display dimensions table"),
        (0x5CD4, 0x5D10, "VI table A"),
        (0x7594, 0x75D0, "VI table B"),
        (0x76F0, 0x7700, "dimension header only"),
    ],
    "core_only": [
        (0x24B8, 0x2500, "display dimensions table"),
        (0x5CD4, 0x5D10, "VI table A"),
        (0x7594, 0x75D0, "VI table B"),
    ],
    "menu_only": [
        (0x9C3C, 0x9D24, "menu/display table A"),
        (0xA240, 0xA264, "menu/display table B"),
    ],
    "direct_only": [],
}


DIRECT_PATCH_GROUPS = {
    "A_init_stride": [
    (0x3C8C, 0x3C010009, "fb size upper for 0x96000"),
    (0x3C90, 0x24216000, "fb size lower for 0x96000"),
    ],
    "B_alloc_reserve": [
    (0x3D30, 0x3C048080, "upper RAM end pointer"),
    (0x3D34, 0x00000000, "clear old RAM end load"),
    (0x3D38, 0x00000000, "clear old RAM end OR"),
    (0x3D3C, 0x3C050012, "double fb size upper for 0x12C000"),
    (0x3D40, 0x34A5C000, "double fb size lower for 0x12C000"),
    ],
    "C_fb_calc": [
    (0x46C8, 0x3C0F0009, "fb size upper for 0x96000"),
    (0x46CC, 0x35EF6000, "fb size lower for 0x96000"),
    (0x46D0, 0x030F0018, "multu t8,t7"),
    (0x46D4, 0x00000000, "clear old subtract path"),
    (0x46D8, 0x00007812, "mflo t7"),
    (0x46DC, 0x00000000, "clear old subtract path"),
    (0x46E8, 0x00000000, "clear old store path"),
    ],
    "D_mem_fn": [
    (0x6584, 0x3C048080, "upper RAM end pointer"),
    (0x6588, 0x00000000, "clear old load"),
    (0x658C, 0x3C020009, "fb size upper for 0x96000"),
    (0x6590, 0x24426000, "fb size lower for 0x96000"),
    ],
    "B_clear_fixed_8040": [
    (0x3D30, 0x3C048040, "fixed fb clear base upper 0x80400000"),
    (0x3D34, 0x00000000, "clear old RAM end load"),
    (0x3D38, 0x00000000, "clear old RAM end OR"),
    (0x3D3C, 0x3C050012, "double fb size upper for 0x12C000"),
    (0x3D40, 0x34A5C000, "double fb size lower for 0x12C000"),
    (0x3D48, 0x00000000, "do not subtract size from fixed base"),
    ],
    "D_fb_fixed_8040": [
    (0x6584, 0x3C048040, "fixed fb0 base upper 0x80400000"),
    (0x6588, 0x3C020009, "fb size upper for 0x96000"),
    (0x658C, 0x34426000, "fb size lower for 0x96000"),
    (0x6590, 0x00822821, "fb1 = fb0 + size"),
    (0x6594, 0x3C02A000, "uncached segment upper"),
    (0x6598, 0x00827025, "fb0 uncached"),
    (0x659C, 0x3C018002, "global pointer base"),
    (0x65A0, 0xAC2E417C, "store fb0 pointer"),
    (0x65A4, 0x00A27825, "fb1 uncached"),
    (0x65A8, 0x03E00008, "return"),
    (0x65AC, 0xAC2F4180, "store fb1 pointer in delay slot"),
    (0x65B0, 0x00000000, "clear old return"),
    (0x65B4, 0x00000000, "clear old delay slot"),
    ],
    "A_single_stride_zero": [
    (0x3C8C, 0x00000825, "single-buffer stride zero"),
    (0x3C90, 0x00000000, "clear old stride lower"),
    ],
    "B_clear_single_8076A000": [
    (0x3D30, 0x3C048076, "single fb clear base upper 0x8076A000"),
    (0x3D34, 0x3484A000, "single fb clear base lower 0x8076A000"),
    (0x3D38, 0x00000000, "clear old RAM end OR"),
    (0x3D3C, 0x3C050009, "single fb size upper for 0x96000"),
    (0x3D40, 0x34A56000, "single fb size lower for 0x96000"),
    (0x3D48, 0x00000000, "do not subtract size from fixed base"),
    ],
    "C_single_offset_zero": [
    (0x46C8, 0x00007825, "single-buffer active offset zero"),
    (0x46CC, 0x00000000, "clear old offset calc"),
    (0x46D0, 0x00000000, "clear old offset calc"),
    (0x46D4, 0x00000000, "clear old offset calc"),
    (0x46D8, 0x00000000, "clear old offset calc"),
    (0x46DC, 0x00000000, "clear old offset calc"),
    (0x46E8, 0x00000000, "clear old offset calc"),
    ],
    "D_fb_single_8076A000": [
    (0x6584, 0x3C048076, "single fb base upper 0x8076A000"),
    (0x6588, 0x3484A000, "single fb base lower 0x8076A000"),
    (0x658C, 0x00802825, "fb1 = fb0 for single buffering"),
    (0x6590, 0x3C02A000, "uncached segment upper"),
    (0x6594, 0x00827025, "fb0 uncached"),
    (0x6598, 0x3C018002, "global pointer base"),
    (0x659C, 0xAC2E417C, "store fb0 pointer"),
    (0x65A0, 0x00A27825, "fb1 uncached"),
    (0x65A4, 0x03E00008, "return"),
    (0x65A8, 0xAC2F4180, "store fb1 pointer in delay slot"),
    (0x65AC, 0x00000000, "clear old fb1 calc"),
    (0x65B0, 0x00000000, "clear old return"),
    (0x65B4, 0x00000000, "clear old delay slot"),
    ],
    "A_split_load_two_globals": [
    (0x3C8C, 0x8CC94180, "load second framebuffer global instead of adding stride"),
    (0x3C90, 0x01214825, "force K1 bit before toggling to cached"),
    (0x3C94, 0x01214826, "convert second framebuffer global K1->K0"),
    ],
    "B_clear_split_8060_8076": [
    (0x3D24, 0xAFBFFFFC, "save ra before stack adjust"),
    (0x3D28, 0x0FC348E0, "zbufDeallocate"),
    (0x3D2C, 0x27BDFFE8, "allocate stack in delay slot"),
    (0x3D30, 0x3C048060, "clear fb0 base upper 0x80600000"),
    (0x3D34, 0x00000000, "fb0 base lower zero"),
    (0x3D38, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D3C, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D40, 0x0C005F10, "clear fb0"),
    (0x3D44, 0x00000000, "clear delay slot"),
    (0x3D48, 0x3C048076, "clear fb1 base upper 0x8076A000"),
    (0x3D4C, 0x3484A000, "clear fb1 base lower 0x8076A000"),
    (0x3D50, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D54, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D58, 0x0C005F10, "clear fb1"),
    (0x3D5C, 0x00000000, "clear delay slot"),
    (0x3D60, 0x8FBF0014, "restore ra"),
    (0x3D64, 0x03E00008, "return"),
    (0x3D68, 0x27BD0018, "restore stack in delay slot"),
    (0x3D6C, 0x00000000, "clear old padding"),
    (0x3D70, 0x00000000, "clear old padding"),
    (0x3D74, 0x00000000, "clear old padding"),
    (0x3D78, 0x00000000, "clear old padding"),
    (0x3D7C, 0x00000000, "clear old padding"),
    (0x3D80, 0x00000000, "clear old padding"),
    (0x3D84, 0x00000000, "clear old padding"),
    (0x3D88, 0x00000000, "clear old padding"),
    (0x3D8C, 0x00000000, "clear old padding"),
    ],
    "C_split_select_global": [
    (0x46B4, 0x3C038006, "load g_ViBackIndex base"),
    (0x46B8, 0x90780879, "load g_ViBackIndex"),
    (0x46BC, 0x0018C080, "index * sizeof(pointer)"),
    (0x46C0, 0x3C048002, "framebuffer global base upper"),
    (0x46C4, 0x00982021, "select framebuffer global address"),
    (0x46C8, 0x0C00012B, "convert selected framebuffer pointer"),
    (0x46CC, 0x8C84417C, "load selected framebuffer global in delay slot"),
    (0x46D0, 0x3C188002, "load g_ViBackData upper"),
    (0x46D4, 0x8F1832A8, "load g_ViBackData"),
    (0x46D8, 0x00000000, "clear old offset calc"),
    (0x46DC, 0x00000000, "clear old offset calc"),
    (0x46E0, 0x00000000, "clear old offset calc"),
    (0x46E4, 0x00000000, "clear old offset calc"),
    (0x46E8, 0x00000000, "clear old offset calc"),
    (0x46EC, 0x0040C825, "selected framebuffer pointer"),
    (0x46F0, 0xAF190028, "store selected framebuffer pointer"),
    ],
    "C_split_select_global_virtual": [
    (0x46B4, 0x3C038006, "load g_ViBackIndex base"),
    (0x46B8, 0x90780879, "load g_ViBackIndex"),
    (0x46BC, 0x0018C080, "index * sizeof(pointer)"),
    (0x46C0, 0x3C198002, "framebuffer global base upper"),
    (0x46C4, 0x0338C821, "select framebuffer global address"),
    (0x46C8, 0x8F39417C, "load selected virtual framebuffer pointer"),
    (0x46CC, 0x3C188002, "load g_ViBackData upper"),
    (0x46D0, 0x8F1832A8, "load g_ViBackData"),
    (0x46D4, 0x00000000, "clear old physical pointer conversion"),
    (0x46D8, 0x00000000, "clear old offset calc"),
    (0x46DC, 0x00000000, "clear old offset calc"),
    (0x46E0, 0x00000000, "clear old offset calc"),
    (0x46E4, 0x00000000, "clear old offset calc"),
    (0x46E8, 0x00000000, "clear old offset calc"),
    (0x46EC, 0x00000000, "clear old physical pointer move"),
    (0x46F0, 0xAF190028, "store selected virtual framebuffer pointer"),
    ],
    "D_fb_split_8060_8076": [
    (0x6584, 0x3C048060, "fb0 base upper 0x80600000"),
    (0x6588, 0x34840000, "fb0 base lower 0x80600000"),
    (0x658C, 0x3C058076, "fb1 base upper 0x8076A000"),
    (0x6590, 0x34A5A000, "fb1 base lower 0x8076A000"),
    (0x6594, 0x3C02A000, "uncached segment upper"),
    (0x6598, 0x00827025, "fb0 uncached"),
    (0x659C, 0x3C018002, "global pointer base"),
    (0x65A0, 0xAC2E417C, "store fb0 pointer"),
    (0x65A4, 0x00A27825, "fb1 uncached"),
    (0x65A8, 0x03E00008, "return"),
    (0x65AC, 0xAC2F4180, "store fb1 pointer in delay slot"),
    (0x65B0, 0x00000000, "clear old return"),
    (0x65B4, 0x00000000, "clear old delay slot"),
    ],
    "B_clear_split_8040_8076": [
    (0x3D24, 0xAFBFFFFC, "save ra before stack adjust"),
    (0x3D28, 0x0FC348E0, "zbufDeallocate"),
    (0x3D2C, 0x27BDFFE8, "allocate stack in delay slot"),
    (0x3D30, 0x3C048040, "clear fb0 base upper 0x80400000"),
    (0x3D34, 0x00000000, "fb0 base lower zero"),
    (0x3D38, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D3C, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D40, 0x0C005F10, "clear fb0"),
    (0x3D44, 0x00000000, "clear delay slot"),
    (0x3D48, 0x3C048076, "clear fb1 base upper 0x8076A000"),
    (0x3D4C, 0x3484A000, "clear fb1 base lower 0x8076A000"),
    (0x3D50, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D54, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D58, 0x0C005F10, "clear fb1"),
    (0x3D5C, 0x00000000, "clear delay slot"),
    (0x3D60, 0x8FBF0014, "restore ra"),
    (0x3D64, 0x03E00008, "return"),
    (0x3D68, 0x27BD0018, "restore stack in delay slot"),
    (0x3D6C, 0x00000000, "clear old padding"),
    (0x3D70, 0x00000000, "clear old padding"),
    (0x3D74, 0x00000000, "clear old padding"),
    (0x3D78, 0x00000000, "clear old padding"),
    (0x3D7C, 0x00000000, "clear old padding"),
    (0x3D80, 0x00000000, "clear old padding"),
    (0x3D84, 0x00000000, "clear old padding"),
    (0x3D88, 0x00000000, "clear old padding"),
    (0x3D8C, 0x00000000, "clear old padding"),
    ],
    "B_clear_split_8030_8076": [
    (0x3D24, 0xAFBFFFFC, "save ra before stack adjust"),
    (0x3D28, 0x0FC348E0, "zbufDeallocate"),
    (0x3D2C, 0x27BDFFE8, "allocate stack in delay slot"),
    (0x3D30, 0x3C048030, "clear fb0 base upper 0x80300000"),
    (0x3D34, 0x00000000, "fb0 base lower zero"),
    (0x3D38, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D3C, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D40, 0x0C005F10, "clear fb0"),
    (0x3D44, 0x00000000, "clear delay slot"),
    (0x3D48, 0x3C048076, "clear fb1 base upper 0x8076A000"),
    (0x3D4C, 0x3484A000, "clear fb1 base lower 0x8076A000"),
    (0x3D50, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D54, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D58, 0x0C005F10, "clear fb1"),
    (0x3D5C, 0x00000000, "clear delay slot"),
    (0x3D60, 0x8FBF0014, "restore ra"),
    (0x3D64, 0x03E00008, "return"),
    (0x3D68, 0x27BD0018, "restore stack in delay slot"),
    (0x3D6C, 0x00000000, "clear old padding"),
    (0x3D70, 0x00000000, "clear old padding"),
    (0x3D74, 0x00000000, "clear old padding"),
    (0x3D78, 0x00000000, "clear old padding"),
    (0x3D7C, 0x00000000, "clear old padding"),
    (0x3D80, 0x00000000, "clear old padding"),
    (0x3D84, 0x00000000, "clear old padding"),
    (0x3D88, 0x00000000, "clear old padding"),
    (0x3D8C, 0x00000000, "clear old padding"),
    ],
    "B_clear_contig_8030_8039": [
    (0x3D24, 0xAFBFFFFC, "save ra before stack adjust"),
    (0x3D28, 0x0FC348E0, "zbufDeallocate"),
    (0x3D2C, 0x27BDFFE8, "allocate stack in delay slot"),
    (0x3D30, 0x3C048030, "clear fb0 base upper 0x80300000"),
    (0x3D34, 0x00000000, "fb0 base lower zero"),
    (0x3D38, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D3C, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D40, 0x0C005F10, "clear fb0"),
    (0x3D44, 0x00000000, "clear delay slot"),
    (0x3D48, 0x3C048039, "clear fb1 base upper 0x80396000"),
    (0x3D4C, 0x34846000, "clear fb1 base lower 0x80396000"),
    (0x3D50, 0x3C050009, "fb clear size upper for 0x96000"),
    (0x3D54, 0x34A56000, "fb clear size lower for 0x96000"),
    (0x3D58, 0x0C005F10, "clear fb1"),
    (0x3D5C, 0x00000000, "clear delay slot"),
    (0x3D60, 0x8FBF0014, "restore ra"),
    (0x3D64, 0x03E00008, "return"),
    (0x3D68, 0x27BD0018, "restore stack in delay slot"),
    (0x3D6C, 0x00000000, "clear old padding"),
    (0x3D70, 0x00000000, "clear old padding"),
    (0x3D74, 0x00000000, "clear old padding"),
    (0x3D78, 0x00000000, "clear old padding"),
    (0x3D7C, 0x00000000, "clear old padding"),
    (0x3D80, 0x00000000, "clear old padding"),
    (0x3D84, 0x00000000, "clear old padding"),
    (0x3D88, 0x00000000, "clear old padding"),
    (0x3D8C, 0x00000000, "clear old padding"),
    ],
    "D_fb_split_8040_8076": [
    (0x6584, 0x3C048040, "fb0 base upper 0x80400000"),
    (0x6588, 0x34840000, "fb0 base lower 0x80400000"),
    (0x658C, 0x3C058076, "fb1 base upper 0x8076A000"),
    (0x6590, 0x34A5A000, "fb1 base lower 0x8076A000"),
    (0x6594, 0x3C02A000, "uncached segment upper"),
    (0x6598, 0x00827025, "fb0 uncached"),
    (0x659C, 0x3C018002, "global pointer base"),
    (0x65A0, 0xAC2E417C, "store fb0 pointer"),
    (0x65A4, 0x00A27825, "fb1 uncached"),
    (0x65A8, 0x03E00008, "return"),
    (0x65AC, 0xAC2F4180, "store fb1 pointer in delay slot"),
    (0x65B0, 0x00000000, "clear old return"),
    (0x65B4, 0x00000000, "clear old delay slot"),
    ],
    "D_fb_split_8030_8076": [
    (0x6584, 0x3C048030, "fb0 base upper 0x80300000"),
    (0x6588, 0x34840000, "fb0 base lower 0x80300000"),
    (0x658C, 0x3C058076, "fb1 base upper 0x8076A000"),
    (0x6590, 0x34A5A000, "fb1 base lower 0x8076A000"),
    (0x6594, 0x3C02A000, "uncached segment upper"),
    (0x6598, 0x00827025, "fb0 uncached"),
    (0x659C, 0x3C018002, "global pointer base"),
    (0x65A0, 0xAC2E417C, "store fb0 pointer"),
    (0x65A4, 0x00A27825, "fb1 uncached"),
    (0x65A8, 0x03E00008, "return"),
    (0x65AC, 0xAC2F4180, "store fb1 pointer in delay slot"),
    (0x65B0, 0x00000000, "clear old return"),
    (0x65B4, 0x00000000, "clear old delay slot"),
    ],
    "D_fb_contig_8030_8039": [
    (0x6584, 0x3C048030, "fb0 base upper 0x80300000"),
    (0x6588, 0x34840000, "fb0 base lower 0x80300000"),
    (0x658C, 0x3C058039, "fb1 base upper 0x80396000"),
    (0x6590, 0x34A56000, "fb1 base lower 0x80396000"),
    (0x6594, 0x3C02A000, "uncached segment upper"),
    (0x6598, 0x00827025, "fb0 uncached"),
    (0x659C, 0x3C018002, "global pointer base"),
    (0x65A0, 0xAC2E417C, "store fb0 pointer"),
    (0x65A4, 0x00A27825, "fb1 uncached"),
    (0x65A8, 0x03E00008, "return"),
    (0x65AC, 0xAC2F4180, "store fb1 pointer in delay slot"),
    (0x65B0, 0x00000000, "clear old return"),
    (0x65B4, 0x00000000, "clear old delay slot"),
    ],
    "E_direct_dims": [
    (0x4F354, 0x028001E0, "direct render dimensions table 0"),
    (0x4F35C, 0x028001E0, "direct render dimensions table 1"),
    ],
    "E_direct_dim0": [
    (0x4F354, 0x028001E0, "direct render dimensions table 0"),
    ],
    "E_direct_dim1": [
    (0x4F35C, 0x028001E0, "direct render dimensions table 1"),
    ],
    "E_direct_dim1_width640": [
    (0x4F35C, 0x0280014A, "direct render dimensions table 1 width 640, height stock 330"),
    ],
    "E_direct_dim1_height480": [
    (0x4F35C, 0x01B801E0, "direct render dimensions table 1 width stock 440, height 480"),
    ],
    "I_gameplay_viewport_480i": [
    (0xBB730, 0x24020280, "getWidth320or440 low-res return 640"),
    (0xBB740, 0x24020280, "getWidth320or440 hi-res return 640"),
    (0xBB754, 0x240201E0, "getHeight330or240 low-res return 480"),
    (0xBB764, 0x240201E0, "getHeight330or240 hi-res return 480"),
    (0xBB790, 0x2402013F, "viewport width 4-player return 319"),
    (0xBB7A4, 0x24020280, "viewport width hi-res return 640"),
    (0xBB7C0, 0x24020280, "viewport width widescreen return 640"),
    (0xBB7D4, 0x24020280, "viewport width cinema branch return 640"),
    (0xBB7DC, 0x24020280, "viewport width cinema return 640"),
    (0xBB7E0, 0x24020280, "viewport width fallback return 640"),
    (0xBB83C, 0x24020141, "viewport ULX 4-player return 321"),
    (0xBB874, 0x240200E5, "viewport height 4-player return 229"),
    (0xBB89C, 0x240201F0, "viewport height fullscreen hi-res return 496"),
    (0xBB8B8, 0x2402017C, "viewport height widescreen return 380"),
    (0xBB8C0, 0x24020260, "viewport height cinema return 608"),
    (0xBB8FC, 0x24420168, "viewport height widescreen animated offset 360"),
    (0xBB91C, 0x240201B8, "viewport height default return 440"),
    (0xBB944, 0x24420110, "viewport height cinema animated offset 272"),
    (0xBB954, 0x240201B8, "viewport height fallback return 440"),
    (0xBB9A0, 0x240200F1, "viewport ULY 2-player return 241"),
    (0xBB9D8, 0x240200F1, "viewport ULY 4-player return 241"),
    (0xBBA60, 0x2442003C, "viewport ULY widescreen animated offset 60"),
    (0xBBA80, 0x24020014, "viewport ULY default return 20"),
    (0xBBAA8, 0x24420068, "viewport ULY cinema animated offset 104"),
    ],
    "I_gameplay_xy_480i": [
    (0xBB730, 0x24020280, "getWidth320or440 low-res return 640"),
    (0xBB740, 0x24020280, "getWidth320or440 hi-res return 640"),
    (0xBB754, 0x240201E0, "getHeight330or240 low-res return 480"),
    (0xBB764, 0x240201E0, "getHeight330or240 hi-res return 480"),
    ],
    "I_gameplay_view_width_480i": [
    (0xBB790, 0x2402013F, "viewport width 4-player return 319"),
    (0xBB7A4, 0x24020280, "viewport width hi-res return 640"),
    (0xBB7C0, 0x24020280, "viewport width widescreen return 640"),
    (0xBB7D4, 0x24020280, "viewport width cinema branch return 640"),
    (0xBB7DC, 0x24020280, "viewport width cinema return 640"),
    (0xBB7E0, 0x24020280, "viewport width fallback return 640"),
    (0xBB83C, 0x24020141, "viewport ULX 4-player return 321"),
    ],
    "I_gameplay_view_height_480i": [
    (0xBB874, 0x240200E5, "viewport height 4-player return 229"),
    (0xBB89C, 0x240201F0, "viewport height fullscreen hi-res return 496"),
    (0xBB8B8, 0x2402017C, "viewport height widescreen return 380"),
    (0xBB8C0, 0x24020260, "viewport height cinema return 608"),
    (0xBB8FC, 0x24420168, "viewport height widescreen animated offset 360"),
    (0xBB91C, 0x240201B8, "viewport height default return 440"),
    (0xBB944, 0x24420110, "viewport height cinema animated offset 272"),
    (0xBB954, 0x240201B8, "viewport height fallback return 440"),
    ],
    "I_gameplay_view_uly_480i": [
    (0xBB9A0, 0x240200F1, "viewport ULY 2-player return 241"),
    (0xBB9D8, 0x240200F1, "viewport ULY 4-player return 241"),
    (0xBBA60, 0x2442003C, "viewport ULY widescreen animated offset 60"),
    (0xBBA80, 0x24020014, "viewport ULY default return 20"),
    (0xBBAA8, 0x24420068, "viewport ULY cinema animated offset 104"),
    ],
    "I_gameplay_fullscreen_view_480i": [
    (0xBB7A4, 0x24020280, "viewport width hi-res return 640"),
    (0xBB89C, 0x240201F0, "viewport height fullscreen hi-res return 496"),
    (0xBB91C, 0x240201B8, "viewport height default return 440"),
    (0xBB954, 0x240201B8, "viewport height fallback return 440"),
    (0xBBA80, 0x24020014, "viewport ULY default return 20"),
    ],
    "I_gameplay_tnd_fullscreen_view_640x480": [
    (0xBB7A4, 0x24020280, "TND fullscreen viewport width when cameraBufferToggle is set"),
    (0xBB7C0, 0x24020280, "TND single-player widescreen viewport width"),
    (0xBB7D4, 0x24020280, "TND single-player default viewport width branch delay"),
    (0xBB7DC, 0x24020280, "TND single-player cinema viewport width"),
    (0xBB7E0, 0x24020280, "TND single-player fallback viewport width"),
    (0xBB89C, 0x240201E0, "TND cameraBufferToggle widescreen viewport height"),
    (0xBB8B8, 0x240201E0, "TND cameraBufferToggle cinema viewport height"),
    (0xBB8C0, 0x240201E0, "TND cameraBufferToggle fullscreen viewport height"),
    (0xBB91C, 0x240201E0, "TND single-player default viewport height branch delay"),
    (0xBB954, 0x240201E0, "TND single-player fallback viewport height"),
    (0xBBA00, 0x24020000, "TND cameraBufferToggle widescreen viewport top"),
    (0xBBA1C, 0x24020000, "TND cameraBufferToggle cinema viewport top"),
    (0xBBA24, 0x24020000, "TND cameraBufferToggle fullscreen viewport top"),
    (0xBBA80, 0x24020000, "TND single-player default viewport top"),
    ],
    "I_gameplay_tnd_default_ge_view_480i": [
    (0xBB7C0, 0x24020280, "TND non-camera widescreen viewport width"),
    (0xBB7D4, 0x24020280, "TND non-camera default viewport width branch delay"),
    (0xBB7DC, 0x24020280, "TND non-camera cinema viewport width"),
    (0xBB7E0, 0x24020280, "TND non-camera fallback viewport width"),
    (0xBB91C, 0x240201B8, "GE 480i non-camera default viewport height branch delay"),
    (0xBB954, 0x240201B8, "GE 480i non-camera fallback viewport height"),
    (0xBBA80, 0x24020014, "GE 480i non-camera default viewport top"),
    ],
    "I_gameplay_tnd_default_width_480i": [
    (0xBB7C0, 0x24020280, "TND non-camera widescreen viewport width"),
    (0xBB7D4, 0x24020280, "TND non-camera default viewport width branch delay"),
    (0xBB7DC, 0x24020280, "TND non-camera cinema viewport width"),
    (0xBB7E0, 0x24020280, "TND non-camera fallback viewport width"),
    ],
    "I_gameplay_tnd_default_height_480i": [
    (0xBB91C, 0x240201B8, "GE 480i non-camera default viewport height branch delay"),
    (0xBB954, 0x240201B8, "GE 480i non-camera fallback viewport height"),
    ],
    "I_gameplay_tnd_default_height_480_full_480i": [
    (0xBB91C, 0x240201E0, "TND non-camera default viewport height 480 branch delay"),
    (0xBB954, 0x240201E0, "TND non-camera fallback viewport height 480"),
    ],
    "I_gameplay_tnd_default_top_480i": [
    (0xBBA80, 0x24020014, "GE 480i non-camera default viewport top"),
    ],
    "I_gameplay_tnd_default_top_zero_480i": [
    (0xBBA80, 0x24020000, "TND non-camera default viewport top 0"),
    ],
    "I_gameplay_tnd_default_width_height_480i": [
    (0xBB7C0, 0x24020280, "TND non-camera widescreen viewport width"),
    (0xBB7D4, 0x24020280, "TND non-camera default viewport width branch delay"),
    (0xBB7DC, 0x24020280, "TND non-camera cinema viewport width"),
    (0xBB7E0, 0x24020280, "TND non-camera fallback viewport width"),
    (0xBB91C, 0x240201B8, "GE 480i non-camera default viewport height branch delay"),
    (0xBB954, 0x240201B8, "GE 480i non-camera fallback viewport height"),
    ],
    "I_gameplay_tnd_camera_ge_view_480i": [
    (0xBB7A4, 0x24020280, "TND cameraBufferToggle viewport width"),
    (0xBB89C, 0x240201F0, "GE 480i camera widescreen viewport height"),
    (0xBB8B8, 0x2402017C, "GE 480i camera cinema viewport height"),
    (0xBB8C0, 0x24020260, "GE 480i camera fullscreen viewport height"),
    ],
    "I_gameplay_tnd_camera_width_480i": [
    (0xBB7A4, 0x24020280, "TND cameraBufferToggle viewport width"),
    ],
    "I_gameplay_tnd_camera_height_480i": [
    (0xBB89C, 0x240201F0, "GE 480i camera widescreen viewport height"),
    (0xBB8B8, 0x2402017C, "GE 480i camera cinema viewport height"),
    (0xBB8C0, 0x24020260, "GE 480i camera fullscreen viewport height"),
    ],
    "I_gameplay_tnd_camera_height_full_480i": [
    (0xBB89C, 0x240201E0, "TND camera widescreen viewport height 480"),
    (0xBB8B8, 0x240201E0, "TND camera cinema viewport height 480"),
    (0xBB8C0, 0x240201E0, "TND camera fullscreen viewport height 480"),
    ],
    "I_gameplay_tnd_camera_height_stock": [
    (0xBB89C, 0x240200F8, "stock camera widescreen viewport height"),
    (0xBB8B8, 0x240200BE, "stock camera cinema viewport height"),
    (0xBB8C0, 0x24020130, "stock camera fullscreen viewport height"),
    ],
    "I_gameplay_tnd_camera_top_zero": [
    (0xBBA00, 0x24020000, "TND camera widescreen viewport top 0"),
    (0xBBA1C, 0x24020000, "TND camera cinema viewport top 0"),
    (0xBBA24, 0x24020000, "TND camera fullscreen viewport top 0"),
    ],
    "I_gameplay_tnd_ge_view_keep_camera_top_480i": [
    (0xBB7A4, 0x24020280, "TND cameraBufferToggle viewport width"),
    (0xBB7C0, 0x24020280, "TND non-camera widescreen viewport width"),
    (0xBB7D4, 0x24020280, "TND non-camera default viewport width branch delay"),
    (0xBB7DC, 0x24020280, "TND non-camera cinema viewport width"),
    (0xBB7E0, 0x24020280, "TND non-camera fallback viewport width"),
    (0xBB89C, 0x240201F0, "GE 480i camera widescreen viewport height"),
    (0xBB8B8, 0x2402017C, "GE 480i camera cinema viewport height"),
    (0xBB8C0, 0x24020260, "GE 480i camera fullscreen viewport height"),
    (0xBB91C, 0x240201B8, "GE 480i non-camera default viewport height branch delay"),
    (0xBB954, 0x240201B8, "GE 480i non-camera fallback viewport height"),
    (0xBBA80, 0x24020014, "GE 480i non-camera default viewport top"),
    ],
    "J_front_title_480i": [
    (0x43A48, 0x24190097, "title/menu layout Y constant"),
    (0x43A5C, 0x24780104, "title/menu layout Y offset"),
    (0x43A6C, 0x246600F3, "title/menu layout Y offset"),
    (0x43A78, 0x24070109, "title/menu draw height"),
    (0x43ABC, 0x267300F5, "title/menu layout Y offset"),
    (0x460A8, 0x8FAC0054, "title/menu layout use computed top"),
    (0x460AC, 0x8FAB0058, "title/menu layout use computed bottom"),
    (0x460B0, 0x258C0005, "title/menu layout bottom adjustment"),
    (0x460C0, 0x258E000E, "title/menu layout derived extent"),
    (0x460D4, 0x2565FFFE, "title/menu layout derived x"),
    (0x460D8, 0x2586FFFF, "title/menu layout derived y"),
    (0x460E0, 0x24E70057, "title/menu layout offset"),
    (0x46EB8, 0x3C0143F0, "title/menu float constant upper"),
    (0x46ED8, 0x3C064420, "title/menu float constant upper"),
    (0x46F18, 0x241801E0, "title/menu height limit 480"),
    (0x46F1C, 0x26AE0033, "title/menu y offset"),
    (0x46F20, 0x26AA003D, "title/menu y offset"),
    (0x4AAAC, 0x240A0050, "title/menu layout x constant"),
    (0x4AAB0, 0x240B00F3, "title/menu layout y constant"),
    (0x4AAC4, 0x240401D1, "title/menu draw width"),
    (0x4D42C, 0x24050280, "front zbuffer width 640"),
    (0x4D434, 0x240601E0, "front zbuffer height 480"),
    (0x4DAE0, 0x24040280, "front viSetXY/menu width 640"),
    (0x4DAE8, 0x240501E0, "front viSetXY/menu height 480"),
    (0x4DAEC, 0x24040280, "front viSetBuf/menu width 640"),
    (0x4DAF4, 0x240501E0, "front viSetBuf/menu height 480"),
    (0x50148, 0x2519001D, "title/menu grid x step"),
    (0x50168, 0x2519001C, "title/menu grid x step"),
    (0x501AC, 0x292101AE, "title/menu grid row count"),
    (0x501B4, 0x26100280, "title/menu grid stride 640"),
    (0x106ED4, 0x240F0280, "expanded menu width 640"),
    (0x106EE4, 0x241801E0, "expanded menu height 480"),
    (0x106EF0, 0x24190280, "expanded low-res menu width 640"),
    (0x106F10, 0x240801E0, "expanded low-res menu height 480"),
    (0x106F24, 0x240901E0, "expanded split viewport height 480"),
    ],
    "J_front_resolution_480i": [
    (0x4D42C, 0x24050280, "front zbuffer width 640"),
    (0x4D434, 0x240601E0, "front zbuffer height 480"),
    (0x4DAE0, 0x24040280, "front viSetXY/menu width 640"),
    (0x4DAE8, 0x240501E0, "front viSetXY/menu height 480"),
    (0x4DAEC, 0x24040280, "front viSetBuf/menu width 640"),
    (0x4DAF4, 0x240501E0, "front viSetBuf/menu height 480"),
    ],
    "J_front_zbuffer_480i": [
    (0x4D42C, 0x24050280, "front zbuffer width 640"),
    (0x4D434, 0x240601E0, "front zbuffer height 480"),
    ],
    "J_front_zbuffer_width_640": [
    (0x4D42C, 0x24050280, "front zbuffer width 640 only"),
    ],
    "J_front_zbuffer_height_480": [
    (0x4D434, 0x240601E0, "front zbuffer height 480 only"),
    ],
    "J_front_visetxy_480i": [
    (0x4DAE0, 0x24040280, "front viSetXY/menu width 640"),
    (0x4DAE8, 0x240501E0, "front viSetXY/menu height 480"),
    ],
    "J_front_visetbuf_480i": [
    (0x4DAEC, 0x24040280, "front viSetBuf/menu width 640"),
    (0x4DAF4, 0x240501E0, "front viSetBuf/menu height 480"),
    ],
    "J_front_visetxybuf_480i": [
    (0x4DAE0, 0x24040280, "front viSetXY/menu width 640"),
    (0x4DAE8, 0x240501E0, "front viSetXY/menu height 480"),
    (0x4DAEC, 0x24040280, "front viSetBuf/menu width 640"),
    (0x4DAF4, 0x240501E0, "front viSetBuf/menu height 480"),
    ],
    "J_mission_select_text_480i": [
    (0x43148, 0x24C6002A, "mission select text/grid y offset"),
    (0x43150, 0x24A5FFD3, "mission select text/grid x offset"),
    (0x431E0, 0x24C6002A, "mission select text/grid y offset repeat"),
    (0x431E4, 0x24A5FFD3, "mission select text/grid x offset repeat"),
    ],
    "J_front_height_limit_480i": [
    (0x46F18, 0x241801E0, "title/menu height limit 480"),
    ],
    "J_front_layout_43a_480i": [
    (0x43A48, 0x24190097, "title/menu layout Y constant"),
    (0x43A5C, 0x24780104, "title/menu layout Y offset"),
    (0x43A6C, 0x246600F3, "title/menu layout Y offset"),
    (0x43A78, 0x24070109, "title/menu draw height"),
    (0x43ABC, 0x267300F5, "title/menu layout Y offset"),
    ],
    "J_front_layout_460_480i": [
    (0x460A8, 0x8FAC0054, "title/menu layout use computed top"),
    (0x460AC, 0x8FAB0058, "title/menu layout use computed bottom"),
    (0x460B0, 0x258C0005, "title/menu layout bottom adjustment"),
    (0x460C0, 0x258E000E, "title/menu layout derived extent"),
    (0x460D4, 0x2565FFFE, "title/menu layout derived x"),
    (0x460D8, 0x2586FFFF, "title/menu layout derived y"),
    (0x460E0, 0x24E70057, "title/menu layout offset"),
    ],
    "J_front_layout_float_480i": [
    (0x46EB8, 0x3C0143F0, "title/menu float constant upper"),
    (0x46ED8, 0x3C064420, "title/menu float constant upper"),
    ],
    "J_front_layout_y_480i": [
    (0x46F1C, 0x26AE0033, "title/menu y offset"),
    (0x46F20, 0x26AA003D, "title/menu y offset"),
    ],
    "J_front_layout_4aaa_480i": [
    (0x4AAAC, 0x240A0050, "title/menu layout x constant"),
    (0x4AAB0, 0x240B00F3, "title/menu layout y constant"),
    (0x4AAC4, 0x240401D1, "title/menu draw width"),
    ],
    "J_front_layout_gridstep_480i": [
    (0x50148, 0x2519001D, "title/menu grid x step"),
    (0x50168, 0x2519001C, "title/menu grid x step"),
    ],
    "J_front_force_menu_table0_480i": [
    (0x4F1B8, 0x00008025, "force front/menu VI setup to use table entry 0 (current 640x480)"),
    ],
    "J_front_skip_menu_framebuf_swap": [
    (0x4F1C4, 0x10000003, "skip front/menu switch to ptr_menu_videobuffer before applying current table dimensions"),
    ],
    "J_ptr_menu_videobuffer_fixed_8076A000": [
    (0x35920, 0x3C0A8076, "set ptr_menu_videobuffer fixed pointer upper 0x8076"),
    (0x35924, 0x354AA000, "set ptr_menu_videobuffer fixed pointer lower 0xA000"),
    (0x3592C, 0x00000000, "skip allocated ptr_menu_videobuffer alignment mask"),
    (0x35934, 0xAC6A0000, "store fixed ptr_menu_videobuffer pointer"),
    ],
    "J_front_buffer_sizes_480i": [
    (0x3FC90, 0x3C05000B, "front/gunbarrel work buffer size upper for 0xBE200"),
    (0x3FC94, 0x34A5E200, "front/gunbarrel work buffer size lower for 0xBE200"),
    (0x40540, 0x3C0E000B, "front state/work buffer size upper for 0xB4200"),
    (0x40544, 0x35CE4200, "front state/work buffer size lower for 0xB4200"),
    ],
    "J_gefb_stride_exact_from_split": [
    (0x3C8C, 0x3C010009, "GE 480i cfb display-list stride upper"),
    (0x3C90, 0x24216000, "GE 480i cfb display-list stride lower"),
    (0x3C94, 0x01214821, "GE 480i cfb display-list second buffer add"),
    ],
    "J_gefb_clear_exact_from_split": [
    (0x3D30, 0x3C048080, "GE 480i clear base upper 0x8080"),
    (0x3D34, 0x00000000, "GE 480i clear base lower/nop"),
    (0x3D38, 0x00000000, "GE 480i clear setup nop"),
    (0x3D3C, 0x3C050012, "GE 480i clear size upper 0x12"),
    (0x3D40, 0x34A5C000, "GE 480i clear size lower 0xC000"),
    (0x3D44, 0x0C005F10, "GE 480i clear call"),
    (0x3D48, 0x00852023, "GE 480i clear start = 0x80800000 - 0x12C000"),
    (0x3D4C, 0x8FBF0014, "GE 480i clear epilogue load ra"),
    (0x3D50, 0x03E00008, "GE 480i clear return"),
    (0x3D54, 0x27BD0018, "GE 480i clear stack restore"),
    (0x3D58, 0x00000000, "remove split-buffer second clear"),
    (0x3D5C, 0x00000000, "remove split-buffer second clear"),
    (0x3D60, 0x00000000, "remove split-buffer second clear"),
    (0x3D64, 0x00000000, "remove split-buffer second clear"),
    (0x3D68, 0x00000000, "remove split-buffer second clear"),
    ],
    "J_gefb_vi_calc_exact_from_split": [
    (0x46B4, 0x3C048002, "GE 480i VI cfb base global upper"),
    (0x46B8, 0x0C00012B, "GE 480i VI uncached address call"),
    (0x46BC, 0x8C84417C, "GE 480i VI cfb0 load"),
    (0x46C0, 0x3C038006, "GE 480i VI back-index upper"),
    (0x46C4, 0x90780879, "GE 480i VI back-index load"),
    (0x46C8, 0x3C0F0009, "GE 480i VI frame stride upper"),
    (0x46CC, 0x35EF6000, "GE 480i VI frame stride lower"),
    (0x46D0, 0x030F0018, "GE 480i VI back-index stride multiply"),
    (0x46D4, 0x00000000, "GE 480i VI multiply delay"),
    (0x46D8, 0x00007812, "GE 480i VI stride product"),
    (0x46DC, 0x00000000, "GE 480i VI product delay"),
    (0x46E0, 0x3C188002, "GE 480i VI task pointer upper"),
    (0x46E4, 0x8F1832A8, "GE 480i VI task pointer load"),
    (0x46E8, 0x00000000, "GE 480i VI task delay"),
    (0x46EC, 0x01E2C821, "GE 480i VI task framebuffer add"),
    (0x46F0, 0xAF190028, "GE 480i VI task framebuffer store"),
    ],
    "J_gefb_pointer_exact_from_split": [
    (0x6584, 0x3C048080, "GE 480i cfb end upper 0x8080"),
    (0x6588, 0x00000000, "GE 480i cfb end lower/nop"),
    (0x658C, 0x3C020009, "GE 480i cfb stride upper"),
    (0x6590, 0x24426000, "GE 480i cfb stride lower"),
    (0x6594, 0x00822823, "GE 480i cfb1 = end - stride"),
    (0x6598, 0x00A22023, "GE 480i cfb0 = cfb1 - stride"),
    (0x659C, 0x3C02A000, "GE 480i uncached segment upper"),
    (0x65A0, 0x00827025, "GE 480i cfb0 uncached"),
    (0x65A4, 0x3C018002, "GE 480i cfb global upper"),
    (0x65A8, 0xAC2E417C, "GE 480i store cfb0"),
    (0x65AC, 0x00A27825, "GE 480i cfb1 uncached"),
    (0x65B0, 0x03E00008, "GE 480i cfb pointer return"),
    (0x65B4, 0xAC2F4180, "GE 480i store cfb1"),
    ],
    "J_front_layout_no_rectloop_480i": [
    (0x43A48, 0x24190097, "title/menu layout Y constant"),
    (0x43A5C, 0x24780104, "title/menu layout Y offset"),
    (0x43A6C, 0x246600F3, "title/menu layout Y offset"),
    (0x43A78, 0x24070109, "title/menu draw height"),
    (0x43ABC, 0x267300F5, "title/menu layout Y offset"),
    (0x460A8, 0x8FAC0054, "title/menu layout use computed top"),
    (0x460AC, 0x8FAB0058, "title/menu layout use computed bottom"),
    (0x460B0, 0x258C0005, "title/menu layout bottom adjustment"),
    (0x460C0, 0x258E000E, "title/menu layout derived extent"),
    (0x460D4, 0x2565FFFE, "title/menu layout derived x"),
    (0x460D8, 0x2586FFFF, "title/menu layout derived y"),
    (0x460E0, 0x24E70057, "title/menu layout offset"),
    (0x46EB8, 0x3C0143F0, "title/menu float constant upper"),
    (0x46ED8, 0x3C064420, "title/menu float constant upper"),
    (0x46F18, 0x241801E0, "title/menu height limit 480"),
    (0x46F1C, 0x26AE0033, "title/menu y offset"),
    (0x46F20, 0x26AA003D, "title/menu y offset"),
    (0x4AAAC, 0x240A0050, "title/menu layout x constant"),
    (0x4AAB0, 0x240B00F3, "title/menu layout y constant"),
    (0x4AAC4, 0x240401D1, "title/menu draw width"),
    (0x50148, 0x2519001D, "title/menu grid x step"),
    (0x50168, 0x2519001C, "title/menu grid x step"),
    ],
    "K_rectloop_640x430": [
    (0x501AC, 0x292101AE, "texture rectangle row loop limit 430"),
    (0x501B4, 0x26100280, "texture rectangle source stride 640"),
    ],
    "K_rectloop_tnd_stride_764_height430": [
    (0x501AC, 0x292101AE, "TND gunbarrel source row loop limit 430"),
    (0x501B4, 0x261002FC, "TND gunbarrel source stride 764"),
    ],
    "K_rectloop_tnd_stride_764_crop480": [
    (0x501AC, 0x292101E0, "TND gunbarrel source row loop limit 480"),
    (0x501B4, 0x261002FC, "TND gunbarrel source stride 764"),
    ],
    "K_rectloop_tnd_stride_764_full509": [
    (0x501AC, 0x292101FD, "TND gunbarrel source row loop limit 509"),
    (0x501B4, 0x261002FC, "TND gunbarrel source stride 764"),
    ],
    "K_rectloop_tnd_stride_508_height430": [
    (0x501AC, 0x292101AE, "TND title RLE source row loop limit 430"),
    (0x501B4, 0x261001FC, "TND title RLE source stride 508"),
    ],
    "K_rectloop_tnd_stride_508_height480": [
    (0x501AC, 0x292101E0, "TND title RLE source row loop limit 480"),
    (0x501B4, 0x261001FC, "TND title RLE source stride 508"),
    ],
    "K_rectloop_tnd_stride_508_full507": [
    (0x501AC, 0x292101FB, "TND title RLE source row loop limit 507"),
    (0x501B4, 0x261001FC, "TND title RLE source stride 508"),
    ],
    "K_title_draw_ge480_target_tnd_stride_764_height430": [
    (0x4FDEC, 0x3C170713, "GE 480i title texture setup upper"),
    (0x4FDFC, 0x3C0AE49F, "GE 480i title texture rectangle target width"),
    (0x4FE34, 0x3C0143D7, "GE 480i title draw height float upper 430.0"),
    (0x4FE3C, 0x36F7F006, "GE 480i title texture setup lower"),
    (0x4FE44, 0x44818000, "GE 480i title draw uses immediate height float"),
    (0x4FF00, 0x3C0E009F, "GE 480i title texture rectangle lower width"),
    (0x500EC, 0x2519001D, "GE 480i title negative-x strip step"),
    (0x500FC, 0x250E001C, "GE 480i title negative-x strip step"),
    (0x50148, 0x2519001D, "GE 480i title positive-x strip step"),
    (0x50168, 0x2519001C, "GE 480i title positive-x strip step"),
    (0x501AC, 0x292101AE, "GE 480i title source row loop limit 430"),
    (0x501B4, 0x261002FC, "TND title source stride 764"),
    ],
    "K_title_draw_ge480_target_tnd_stride_764_height480": [
    (0x4FDEC, 0x3C170713, "GE 480i title texture setup upper"),
    (0x4FDFC, 0x3C0AE49F, "GE 480i title texture rectangle target width"),
    (0x4FE34, 0x3C0143F0, "TND title draw height float upper 480.0"),
    (0x4FE3C, 0x36F7F006, "GE 480i title texture setup lower"),
    (0x4FE44, 0x44818000, "GE 480i title draw uses immediate height float"),
    (0x4FF00, 0x3C0E009F, "GE 480i title texture rectangle lower width"),
    (0x500EC, 0x2519001D, "GE 480i title negative-x strip step"),
    (0x500FC, 0x250E001C, "GE 480i title negative-x strip step"),
    (0x50148, 0x2519001D, "GE 480i title positive-x strip step"),
    (0x50168, 0x2519001C, "GE 480i title positive-x strip step"),
    (0x501AC, 0x292101E0, "TND title source row loop limit 480"),
    (0x501B4, 0x261002FC, "TND title source stride 764"),
    ],
    "K_title_draw_ge480_target_tnd_stride_764_height508": [
    (0x4FDEC, 0x3C170713, "GE 480i title texture setup upper"),
    (0x4FDFC, 0x3C0AE49F, "GE 480i title texture rectangle target width"),
    (0x4FE34, 0x3C0143FE, "TND title draw height float upper 508.0"),
    (0x4FE3C, 0x36F7F006, "GE 480i title texture setup lower"),
    (0x4FE44, 0x44818000, "GE 480i title draw uses immediate height float"),
    (0x4FF00, 0x3C0E009F, "GE 480i title texture rectangle lower width"),
    (0x500EC, 0x2519001D, "GE 480i title negative-x strip step"),
    (0x500FC, 0x250E001C, "GE 480i title negative-x strip step"),
    (0x50148, 0x2519001D, "GE 480i title positive-x strip step"),
    (0x50168, 0x2519001C, "GE 480i title positive-x strip step"),
    (0x501AC, 0x292101FC, "TND title source row loop limit 508"),
    (0x501B4, 0x261002FC, "TND title source stride 764"),
    ],
    "K_title_draw_ge480_target_tnd_stride_508_height430": [
    (0x4FDEC, 0x3C170713, "GE 480i title texture setup upper"),
    (0x4FDFC, 0x3C0AE49F, "GE 480i title texture rectangle target width"),
    (0x4FE34, 0x3C0143D7, "GE 480i title draw height float upper 430.0"),
    (0x4FE3C, 0x36F7F006, "GE 480i title texture setup lower"),
    (0x4FE44, 0x44818000, "GE 480i title draw uses immediate height float"),
    (0x4FF00, 0x3C0E009F, "GE 480i title texture rectangle lower width"),
    (0x500EC, 0x2519001D, "GE 480i title negative-x strip step"),
    (0x500FC, 0x250E001C, "GE 480i title negative-x strip step"),
    (0x50148, 0x2519001D, "GE 480i title positive-x strip step"),
    (0x50168, 0x2519001C, "GE 480i title positive-x strip step"),
    (0x501AC, 0x292101AE, "GE 480i title source row loop limit 430"),
    (0x501B4, 0x261001FC, "TND title RLE source stride 508"),
    ],
    "K_title_draw_ge480_target_asset640_height430": [
    (0x4FDEC, 0x3C170713, "GE 480i title texture setup upper"),
    (0x4FDFC, 0x3C0AE49F, "GE 480i title texture rectangle target width"),
    (0x4FE34, 0x3C0143D7, "GE 480i title draw height float upper 430.0"),
    (0x4FE3C, 0x36F7F006, "GE 480i title texture setup lower"),
    (0x4FE44, 0x44818000, "GE 480i title draw uses immediate height float"),
    (0x4FF00, 0x3C0E009F, "GE 480i title texture rectangle lower width"),
    (0x500EC, 0x2519001D, "GE 480i title negative-x strip step"),
    (0x500FC, 0x250E001C, "GE 480i title negative-x strip step"),
    (0x50148, 0x2519001D, "GE 480i title positive-x strip step"),
    (0x50168, 0x2519001C, "GE 480i title positive-x strip step"),
    (0x501AC, 0x292101AE, "GE 480i title source row loop limit 430"),
    (0x501B4, 0x26100280, "appended 640x430 title RLE source stride"),
    ],
    "K_title_draw_ge480_target_stock_source": [
    (0x4FDEC, 0x3C170713, "GE 480i title texture setup upper"),
    (0x4FDFC, 0x3C0AE49F, "GE 480i title texture rectangle target width"),
    (0x4FE34, 0x3C0143D7, "GE 480i title draw height float upper 430.0"),
    (0x4FE3C, 0x36F7F006, "GE 480i title texture setup lower"),
    (0x4FE44, 0x44818000, "GE 480i title draw uses immediate height float"),
    (0x4FF00, 0x3C0E009F, "GE 480i title texture rectangle lower width"),
    (0x500EC, 0x2519001D, "GE 480i title negative-x strip step"),
    (0x500FC, 0x250E001C, "GE 480i title negative-x strip step"),
    (0x50148, 0x2519001D, "GE 480i title positive-x strip step"),
    (0x50168, 0x2519001C, "GE 480i title positive-x strip step"),
    ],
    "L_skip_file_select_backdrop": [
    (0x41030, 0x00801025, "skip file-select call to shared title backdrop blitter"),
    ],
    "M_skip_postblood_sniper_blitter": [
    (0x3E0EC, 0x00801025, "skip sniper/RLE blitter in post-blood intro state 4"),
    (0x3E198, 0x00801025, "skip sniper/RLE blitter in post-blood intro state 5"),
    ],
    "N_skip_postblood_eye_backdrop": [
    (0x3E0F4, 0x00801025, "skip eye backdrop draw in post-blood intro state 4"),
    (0x3E1A0, 0x00801025, "skip eye backdrop draw in post-blood intro state 5"),
    ],
    "O_skip_case1_sniper_layer": [
    (0x3DEB4, 0x00801025, "diagnostic skip sniper/RLE layer in early intro state 1"),
    ],
    "O_skip_case1_eye_backdrop": [
    (0x3DEBC, 0x00801025, "diagnostic skip eye backdrop layer in early intro state 1"),
    ],
    "O_skip_cases1_3_sniper_layer": [
    (0x3DEB4, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 1"),
    (0x3DF58, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 2"),
    (0x3E00C, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 3"),
    ],
    "O_skip_cases1_3_eye_backdrop": [
    (0x3DEBC, 0x00801025, "diagnostic skip eye backdrop layer in intro state 1"),
    (0x3DF60, 0x00801025, "diagnostic skip eye backdrop layer in intro state 2"),
    (0x3E014, 0x00801025, "diagnostic skip eye backdrop layer in intro state 3"),
    ],
    "O_skip_cases1_5_sniper_layer": [
    (0x3DEB4, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 1"),
    (0x3DF58, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 2"),
    (0x3E00C, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 3"),
    (0x3E0EC, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 4"),
    (0x3E198, 0x00801025, "diagnostic skip sniper/RLE layer in intro state 5"),
    ],
    "O_skip_cases1_5_eye_backdrop": [
    (0x3DEBC, 0x00801025, "diagnostic skip eye backdrop layer in intro state 1"),
    (0x3DF60, 0x00801025, "diagnostic skip eye backdrop layer in intro state 2"),
    (0x3E014, 0x00801025, "diagnostic skip eye backdrop layer in intro state 3"),
    (0x3E0F4, 0x00801025, "diagnostic skip eye backdrop layer in intro state 4"),
    (0x3E1A0, 0x00801025, "diagnostic skip eye backdrop layer in intro state 5"),
    ],
    "P_sniper_slice_divisor_640": [
    (0x3C95C, 0x3C014420, "diagnostic sniper/RLE slice x divisor 640.0"),
    ],
    "P_sniper_slice_divisor_960": [
    (0x3C95C, 0x3C014470, "diagnostic sniper/RLE slice x divisor 960.0"),
    ],
    "P_sniper_slice_divisor_2560": [
    (0x3C95C, 0x3C014520, "diagnostic sniper/RLE slice x divisor 2560.0"),
    ],
    "P_sniper_slice_x_zero": [
    (0x3C980, 0x00002825, "diagnostic sniper/RLE slice x argument forced to zero"),
    ],
    "P_sniper_slice_x_left160": [
    (0x3C980, 0x2405FF60, "diagnostic sniper/RLE slice x argument forced to -160"),
    ],
    "P_sniper_slice_x_right160": [
    (0x3C980, 0x240500A0, "diagnostic sniper/RLE slice x argument forced to +160"),
    ],
    "Q_sniper_skip_internal_rle_blit": [
    (0x3C984, 0x02001025, "diagnostic skip sub_GAME_7F007CC8 inside insert_sniper_sight_eye_intro"),
    ],
    "Q_moving_skip_pre_matrix_barrel_dl": [
    (0x3C624, 0x24180000, "diagnostic disable first moving gunbarrel display-list command"),
    ],
    "Q_moving_skip_post_matrix_barrel_dl": [
    (0x3C68C, 0x240F0000, "diagnostic disable second moving gunbarrel display-list command"),
    ],
    "R_sniper_rle_end_color_zero": [
    (0x3C8F4, 0x00000825, "diagnostic force sniper/RLE end color component 0 to 0"),
    (0x3C8FC, 0x00006825, "diagnostic force sniper/RLE end color component 1 to 0"),
    (0x3C904, 0x00000825, "diagnostic force sniper/RLE end color component 2 to 0"),
    ],
    "R_sniper_rle_end_color_32": [
    (0x3C8F4, 0x24010020, "diagnostic force sniper/RLE end color component 0 to 0x20"),
    (0x3C8FC, 0x240D0020, "diagnostic force sniper/RLE end color component 1 to 0x20"),
    (0x3C904, 0x24010020, "diagnostic force sniper/RLE end color component 2 to 0x20"),
    ],
    "R_sniper_rle_end_color_48": [
    (0x3C8F4, 0x24010030, "diagnostic force sniper/RLE end color component 0 to 0x30"),
    (0x3C8FC, 0x240D0030, "diagnostic force sniper/RLE end color component 1 to 0x30"),
    (0x3C904, 0x24010030, "diagnostic force sniper/RLE end color component 2 to 0x30"),
    ],
    "R_sniper_rle_end_color_64": [
    (0x3C8F4, 0x24010040, "diagnostic force sniper/RLE end color component 0 to 0x40"),
    (0x3C8FC, 0x240D0040, "diagnostic force sniper/RLE end color component 1 to 0x40"),
    (0x3C904, 0x24010040, "diagnostic force sniper/RLE end color component 2 to 0x40"),
    ],
    "R_sniper_rle_end_color_96": [
    (0x3C8F4, 0x24010060, "diagnostic force sniper/RLE end color component 0 to 0x60"),
    (0x3C8FC, 0x240D0060, "diagnostic force sniper/RLE end color component 1 to 0x60"),
    (0x3C904, 0x24010060, "diagnostic force sniper/RLE end color component 2 to 0x60"),
    ],
    "R_sniper_rle_end_color_128": [
    (0x3C8F4, 0x24010080, "diagnostic force sniper/RLE end color component 0 to 0x80"),
    (0x3C8FC, 0x240D0080, "diagnostic force sniper/RLE end color component 1 to 0x80"),
    (0x3C904, 0x24010080, "diagnostic force sniper/RLE end color component 2 to 0x80"),
    ],
    "S_gunbarrel_case1_slow_3_625": [
    (0x3DF04, 0x3C014068, "diagnostic gunbarrel case1 x decrement 3.625 upper"),
    (0x3DF08, 0x44814000, "diagnostic gunbarrel case1 x decrement move to f8"),
    ],
    "T_sniper_call_alt640_blitter": [
    (0x3C8A4, 0x0FC06DB8, "diagnostic route sniper wrapper to adjacent 640-stride blitter"),
    ],
    "U_shared_blitter_stock_texture_setup": [
    (0x4FDEC, 0x3C17070D, "diagnostic restore stock title/sniper texture setup upper"),
    (0x4FDFC, 0x3C0AE46D, "diagnostic restore stock title/sniper texture rectangle target width"),
    (0x4FE34, 0x3C018005, "diagnostic restore stock title/sniper height load upper"),
    (0x4FE3C, 0x36F7B026, "diagnostic restore stock title/sniper texture setup lower"),
    (0x4FE44, 0xC4301CF0, "diagnostic restore stock title/sniper height load"),
    (0x4FF00, 0x3C0E006D, "diagnostic restore stock title/sniper texture rectangle lower width"),
    ],
    "U_shared_blitter_stock_strip_steps": [
    (0x500EC, 0x25190011, "diagnostic restore stock title/sniper negative-x strip step"),
    (0x500FC, 0x250E0010, "diagnostic restore stock title/sniper negative-x strip step"),
    (0x50148, 0x25190011, "diagnostic restore stock title/sniper positive-x strip step"),
    (0x50168, 0x25190010, "diagnostic restore stock title/sniper positive-x strip step"),
    ],
    "U_shared_blitter_stock_row_count": [
    (0x501AC, 0x2921012C, "diagnostic restore stock title/sniper source row loop limit 300"),
    ],
    "U_shared_blitter_stock_stride": [
    (0x501B4, 0x261001B8, "diagnostic restore stock title/sniper source stride 440"),
    ],
    "J_expanded_menu_resolution_480i": [
    (0x106ED4, 0x240F0280, "expanded menu width 640"),
    (0x106EE4, 0x241801E0, "expanded menu height 480"),
    (0x106EF0, 0x24190280, "expanded low-res menu width 640"),
    (0x106F10, 0x240801E0, "expanded low-res menu height 480"),
    (0x106F24, 0x240901E0, "expanded split viewport height 480"),
    ],
    "F_vi_word": [
        (0x441C, 0x00187880, "GE 480i VI-related word"),
    ],
    "G_mask_word": [
        (0x104DC, 0x2401FFFF, "GE 480i mask word"),
    ],
    "H_pi_dma": [
        (0x19978, 0x3C09A440, "GE 480i PI/DMA patch"),
        (0x19980, 0x10000006, "GE 480i PI/DMA patch"),
        (0x19984, 0x00000000, "GE 480i PI/DMA patch"),
        (0x199B4, 0x000C6040, "GE 480i PI/DMA patch"),
        (0x199D0, 0xADEE0018, "GE 480i PI/DMA patch"),
        (0x19A24, 0x8E2B002C, "GE 480i PI/DMA patch"),
        (0x19A60, 0xAD890030, "GE 480i PI/DMA patch"),
        (0x19A64, 0x000B5842, "GE 480i PI/DMA patch"),
    ],
    "H_origin_bypass": [
        (0x19978, 0x3C09A440, "GE 480i VI origin/control-flow bypass"),
        (0x19980, 0x10000006, "GE 480i VI origin/control-flow bypass"),
        (0x19984, 0x00000000, "GE 480i VI origin/control-flow bypass"),
    ],
    "H_width_vsync": [
        (0x199B4, 0x000C6040, "GE 480i VI width/vsync patch"),
        (0x199D0, 0xADEE0018, "GE 480i VI width/vsync patch"),
    ],
    "H_scale": [
        (0x19A24, 0x8E2B002C, "GE 480i VI scale patch"),
        (0x19A60, 0xAD890030, "GE 480i VI scale patch"),
        (0x19A64, 0x000B5842, "GE 480i VI scale patch"),
    ],
    "H_width_scale": [
        (0x199B4, 0x000C6040, "GE 480i VI width/vsync patch"),
        (0x199D0, 0xADEE0018, "GE 480i VI width/vsync patch"),
        (0x19A24, 0x8E2B002C, "GE 480i VI scale patch"),
        (0x19A60, 0xAD890030, "GE 480i VI scale patch"),
        (0x19A64, 0x000B5842, "GE 480i VI scale patch"),
    ],
    "H_origin_width": [
        (0x19978, 0x3C09A440, "GE 480i VI origin/control-flow bypass"),
        (0x19980, 0x10000006, "GE 480i VI origin/control-flow bypass"),
        (0x19984, 0x00000000, "GE 480i VI origin/control-flow bypass"),
        (0x199B4, 0x000C6040, "GE 480i VI width/vsync patch"),
        (0x199D0, 0xADEE0018, "GE 480i VI width/vsync patch"),
    ],
    "H_origin_scale": [
        (0x19978, 0x3C09A440, "GE 480i VI origin/control-flow bypass"),
        (0x19980, 0x10000006, "GE 480i VI origin/control-flow bypass"),
        (0x19984, 0x00000000, "GE 480i VI origin/control-flow bypass"),
        (0x19A24, 0x8E2B002C, "GE 480i VI scale patch"),
        (0x19A60, 0xAD890030, "GE 480i VI scale patch"),
        (0x19A64, 0x000B5842, "GE 480i VI scale patch"),
    ],
}


DIRECT_PATCH_PROFILES = {
    "none": [],
    "dim0_only": ["E_direct_dim0"],
    "dim1_only": ["E_direct_dim1"],
    "dim1_width640_only": ["E_direct_dim1_width640"],
    "dim1_height480_only": ["E_direct_dim1_height480"],
    "dims_only": ["E_direct_dims"],
    "gameplay480i_only": ["I_gameplay_viewport_480i"],
    "gameplayxy480i_only": ["I_gameplay_xy_480i"],
    "gameplayxy_width480i_only": ["I_gameplay_xy_480i", "I_gameplay_view_width_480i"],
    "gameplayxy_height480i_only": ["I_gameplay_xy_480i", "I_gameplay_view_height_480i"],
    "gameplayxy_viewsize480i_only": ["I_gameplay_xy_480i", "I_gameplay_view_width_480i", "I_gameplay_view_height_480i"],
    "gameplayxy_fullscreenview480i_only": ["I_gameplay_xy_480i", "I_gameplay_fullscreen_view_480i"],
    "gameplayxy_tndfullscreen480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_fullscreen_view_640x480"],
    "gameplayxy_tnddefaultgeview480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_ge_view_480i"],
    "gameplayxy_tnddefaultwidth480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i"],
    "gameplayxy_tnddefaultheight480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_height_480i"],
    "gameplayxy_tnddefaultheight480full480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_height_480_full_480i"],
    "gameplayxy_tnddefaulttop480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_top_480i"],
    "gameplayxy_tnddefaulttopzero480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_top_zero_480i"],
    "gameplayxy_tnddefaultwidthheight480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i"],
    "gameplayxy_tnddefaultwidthheighttopzero480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "I_gameplay_tnd_default_top_zero_480i"],
    "gameplayxy_tnddefaultwidthheight480full480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "I_gameplay_tnd_default_height_480_full_480i"],
    "gameplayxy_tnddefaultwidthheight480fulltopzero480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "I_gameplay_tnd_default_height_480_full_480i", "I_gameplay_tnd_default_top_zero_480i"],
    "gameplayxy_tnddefaultwidthheight_tndrect430_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_764_height430"],
    "gameplayxy_tnddefaultwidthheight_tndrect480_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_764_crop480"],
    "gameplayxy_tnddefaultwidthheight_tndrect509_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_764_full509"],
    "gameplayxy_tnddefaultwidthheight_tndrect508src430_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_508_height430"],
    "gameplayxy_tnddefaultwidthheight_tndrect508src480_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_508_height480"],
    "gameplayxy_tnddefaultwidthheight_title640draw_tndstride430_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_tnd_stride_764_height430"],
    "gameplayxy_tnddefaultwidthheight_title640draw_tndstride480_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_tnd_stride_764_height480"],
    "gameplayxy_tnddefaultwidthheight_title640draw_tndstride508_480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_tnd_stride_764_height508"],
    "gameplayxy_tndcamerageview480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_camera_ge_view_480i"],
    "camera_height_full480i_only": ["I_gameplay_tnd_camera_height_full_480i"],
    "camera_height_stock_only": ["I_gameplay_tnd_camera_height_stock"],
    "camera_topzero_only": ["I_gameplay_tnd_camera_top_zero"],
    "camera_height_full480i_topzero_only": ["I_gameplay_tnd_camera_height_full_480i", "I_gameplay_tnd_camera_top_zero"],
    "gameplayxy_tndgeview480i_only": ["I_gameplay_xy_480i", "I_gameplay_tnd_ge_view_keep_camera_top_480i"],
    "front_title_480i_only": ["J_front_title_480i"],
    "front_resolution_480i_only": ["J_front_resolution_480i"],
    "front_zbuffer_480i_only": ["J_front_zbuffer_480i"],
    "front_zbuffer_width_640_only": ["J_front_zbuffer_width_640"],
    "front_zbuffer_height_480_only": ["J_front_zbuffer_height_480"],
    "front_visetxy_480i_only": ["J_front_visetxy_480i"],
    "front_visetbuf_480i_only": ["J_front_visetbuf_480i"],
    "front_visetxybuf_480i_only": ["J_front_visetxybuf_480i"],
    "expanded_menu_resolution_480i_only": ["J_expanded_menu_resolution_480i"],
    "front_visetxy_expanded_menu_480i_only": ["J_front_visetxy_480i", "J_expanded_menu_resolution_480i"],
    "front_visetxybuf_expanded_menu_480i_only": ["J_front_visetxybuf_480i", "J_expanded_menu_resolution_480i"],
    "front_visetxybuf_expanded_camerage_480i_only": ["J_front_visetxybuf_480i", "J_expanded_menu_resolution_480i", "I_gameplay_tnd_camera_ge_view_480i"],
    "front_visetxybuf_expanded_tndgeview_480i_only": ["J_front_visetxybuf_480i", "J_expanded_menu_resolution_480i", "I_gameplay_tnd_ge_view_keep_camera_top_480i"],
    "front_height_limit_480i_only": ["J_front_height_limit_480i"],
    "front_buffer_sizes_480i_only": ["J_front_buffer_sizes_480i"],
    "front_zbuffer_buffer_sizes_480i_only": ["J_front_zbuffer_480i", "J_front_buffer_sizes_480i"],
    "front_zbuffer_buffer_sizes_dim1_480i_only": ["J_front_zbuffer_480i", "J_front_buffer_sizes_480i", "E_direct_dim1"],
    "front_layout_43a_480i_only": ["J_front_layout_43a_480i"],
    "front_layout_43a_buffer_sizes_480i_only": ["J_front_layout_43a_480i", "J_front_buffer_sizes_480i"],
    "front_layout_460_480i_only": ["J_front_layout_460_480i"],
    "front_layout_float_480i_only": ["J_front_layout_float_480i"],
    "front_layout_y_480i_only": ["J_front_layout_y_480i"],
    "front_layout_4aaa_480i_only": ["J_front_layout_4aaa_480i"],
    "front_layout_gridstep_480i_only": ["J_front_layout_gridstep_480i"],
    "front_layout_43a_460_480i_only": ["J_front_layout_43a_480i", "J_front_layout_460_480i"],
    "front_layout_43a_y_480i_only": ["J_front_layout_43a_480i", "J_front_layout_y_480i"],
    "front_layout_43a_y_buffer_sizes_480i_only": ["J_front_layout_43a_480i", "J_front_layout_y_480i", "J_front_buffer_sizes_480i"],
    "front_layout_safe_cluster_480i_only": ["J_front_layout_43a_480i", "J_front_layout_4aaa_480i", "J_front_layout_gridstep_480i"],
    "mission_select_text_480i_only": ["J_mission_select_text_480i"],
    "front_force_menu_table0_480i_only": ["J_front_force_menu_table0_480i"],
    "front_skip_menu_framebuf_swap_only": ["J_front_skip_menu_framebuf_swap"],
    "front_dim1_480i_skip_menufb_only": ["E_direct_dim1", "J_front_skip_menu_framebuf_swap"],
    "front_dim1_width640_skip_menufb_only": ["E_direct_dim1_width640", "J_front_skip_menu_framebuf_swap"],
    "front_dim1_height480_skip_menufb_only": ["E_direct_dim1_height480", "J_front_skip_menu_framebuf_swap"],
    "frontlayout_dim1_480i_only": ["J_front_layout_no_rectloop_480i", "E_direct_dim1"],
    "frontlayout_dim1_skip_menufb_only": ["J_front_layout_no_rectloop_480i", "E_direct_dim1", "J_front_skip_menu_framebuf_swap"],
    "frontlayout_dim1_fixed_menufb_only": ["J_ptr_menu_videobuffer_fixed_8076A000", "J_front_layout_no_rectloop_480i", "E_direct_dim1"],
    "frontlayout_dim1_fixed_menufb_frontzbuf_only": ["J_ptr_menu_videobuffer_fixed_8076A000", "J_front_layout_no_rectloop_480i", "J_front_zbuffer_480i", "E_direct_dim1"],
    "frontlayout_dim1_fixed_menufb_frontxybuf_only": ["J_ptr_menu_videobuffer_fixed_8076A000", "J_front_layout_no_rectloop_480i", "J_front_visetxybuf_480i", "E_direct_dim1"],
    "frontlayout_dim1_fixed_menufb_frontres_only": ["J_ptr_menu_videobuffer_fixed_8076A000", "J_front_layout_no_rectloop_480i", "J_front_resolution_480i", "E_direct_dim1"],
    "frontlayout_dim1_fixed_menufb_gefb_only": ["J_gefb_stride_exact_from_split", "J_gefb_clear_exact_from_split", "J_gefb_vi_calc_exact_from_split", "J_gefb_pointer_exact_from_split", "J_ptr_menu_videobuffer_fixed_8076A000", "J_front_layout_no_rectloop_480i", "E_direct_dim1"],
    "frontlayout_dim1_fixed_menufb_gefb_frontbufs_only": ["J_gefb_stride_exact_from_split", "J_gefb_clear_exact_from_split", "J_gefb_vi_calc_exact_from_split", "J_gefb_pointer_exact_from_split", "J_ptr_menu_videobuffer_fixed_8076A000", "J_front_buffer_sizes_480i", "J_front_layout_no_rectloop_480i", "E_direct_dim1"],
    "front_resolution_hlimit_480i_only": ["J_front_resolution_480i", "J_front_height_limit_480i"],
    "front_resolution_expanded_480i_only": ["J_front_resolution_480i", "J_expanded_menu_resolution_480i"],
    "skip_case1_sniper_only": ["O_skip_case1_sniper_layer"],
    "skip_case1_backdrop_only": ["O_skip_case1_eye_backdrop"],
    "skip_case1_layers_only": ["O_skip_case1_sniper_layer", "O_skip_case1_eye_backdrop"],
    "skip_cases1_3_sniper_only": ["O_skip_cases1_3_sniper_layer"],
    "skip_cases1_3_backdrop_only": ["O_skip_cases1_3_eye_backdrop"],
    "skip_cases1_3_layers_only": ["O_skip_cases1_3_sniper_layer", "O_skip_cases1_3_eye_backdrop"],
    "skip_cases1_5_sniper_only": ["O_skip_cases1_5_sniper_layer"],
    "skip_cases1_5_backdrop_only": ["O_skip_cases1_5_eye_backdrop"],
    "skip_cases1_5_layers_only": ["O_skip_cases1_5_sniper_layer", "O_skip_cases1_5_eye_backdrop"],
    "sniper_slice_div640_only": ["P_sniper_slice_divisor_640"],
    "sniper_slice_div960_only": ["P_sniper_slice_divisor_960"],
    "sniper_slice_div2560_only": ["P_sniper_slice_divisor_2560"],
    "sniper_slice_x_zero_only": ["P_sniper_slice_x_zero"],
    "sniper_slice_x_left160_only": ["P_sniper_slice_x_left160"],
    "sniper_slice_x_right160_only": ["P_sniper_slice_x_right160"],
    "sniper_skip_internal_rle_only": ["Q_sniper_skip_internal_rle_blit"],
    "moving_skip_pre_matrix_barrel_only": ["Q_moving_skip_pre_matrix_barrel_dl"],
    "moving_skip_post_matrix_barrel_only": ["Q_moving_skip_post_matrix_barrel_dl"],
    "moving_skip_both_barrels_only": ["Q_moving_skip_pre_matrix_barrel_dl", "Q_moving_skip_post_matrix_barrel_dl"],
    "sniper_rle_end_color_zero_only": ["R_sniper_rle_end_color_zero"],
    "sniper_rle_end_color_32_only": ["R_sniper_rle_end_color_32"],
    "sniper_rle_end_color_64_only": ["R_sniper_rle_end_color_64"],
    "sniper_rle_end_color_96_only": ["R_sniper_rle_end_color_96"],
    "sniper_rle_end_color_128_only": ["R_sniper_rle_end_color_128"],
    "gunbarrel_case1_slow_3_625_only": ["S_gunbarrel_case1_slow_3_625"],
    "gunbarrel_slow_3_625_rle_end_color_64": ["S_gunbarrel_case1_slow_3_625", "R_sniper_rle_end_color_64"],
    "gunbarrel_slow_3_625_rle_end_color_96": ["S_gunbarrel_case1_slow_3_625", "R_sniper_rle_end_color_96"],
    "rle_end_color_32_only": ["R_sniper_rle_end_color_32"],
    "rle_end_color_48_only": ["R_sniper_rle_end_color_48"],
    "rle_end_color_64_only": ["R_sniper_rle_end_color_64"],
    "sniper_call_alt640_blitter_only": ["T_sniper_call_alt640_blitter"],
    "shared_blitter_stock_texture_setup_only": ["U_shared_blitter_stock_texture_setup"],
    "shared_blitter_stock_strip_steps_only": ["U_shared_blitter_stock_strip_steps"],
    "shared_blitter_stock_row_count_only": ["U_shared_blitter_stock_row_count"],
    "shared_blitter_stock_stride_only": ["U_shared_blitter_stock_stride"],
    "shared_blitter_stock_row_stride_only": ["U_shared_blitter_stock_row_count", "U_shared_blitter_stock_stride"],
    "shared_blitter_stock_texture_steps_only": ["U_shared_blitter_stock_texture_setup", "U_shared_blitter_stock_strip_steps"],
    "shared_blitter_stock_all_only": ["U_shared_blitter_stock_texture_setup", "U_shared_blitter_stock_strip_steps", "U_shared_blitter_stock_row_count", "U_shared_blitter_stock_stride"],
    "gunbarrel_slow_3_625_shared_blitter_stock_texture_setup": ["S_gunbarrel_case1_slow_3_625", "U_shared_blitter_stock_texture_setup"],
    "gunbarrel_slow_3_625_shared_blitter_stock_row_stride": ["S_gunbarrel_case1_slow_3_625", "U_shared_blitter_stock_row_count", "U_shared_blitter_stock_stride"],
    "gunbarrel_slow_3_625_shared_blitter_stock_all": ["S_gunbarrel_case1_slow_3_625", "U_shared_blitter_stock_texture_setup", "U_shared_blitter_stock_strip_steps", "U_shared_blitter_stock_row_count", "U_shared_blitter_stock_stride"],
    "f_only": ["F_vi_word"],
    "g_only": ["G_mask_word"],
    "fg_only": ["F_vi_word", "G_mask_word"],
    "h_only": ["H_pi_dma"],
    "h_origin_only": ["H_origin_bypass"],
    "h_width_only": ["H_width_vsync"],
    "h_scale_only": ["H_scale"],
    "fg_h_only": ["F_vi_word", "G_mask_word", "H_pi_dma"],
    "physicalfb_select_only": ["C_split_select_global"],
    "mem_nodims": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn"],
    "mem_dims": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn", "E_direct_dims"],
    "other": ["F_vi_word", "G_mask_word", "H_pi_dma"],
    "all_nodims": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "all": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn", "E_direct_dims", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "fixed8040_mem_nodims": ["A_init_stride", "B_clear_fixed_8040", "C_fb_calc", "D_fb_fixed_8040"],
    "fixed8040_all_nodims": ["A_init_stride", "B_clear_fixed_8040", "C_fb_calc", "D_fb_fixed_8040", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "contig8030_8039_mem_nodims": ["A_init_stride", "B_clear_contig_8030_8039", "C_fb_calc", "D_fb_contig_8030_8039"],
    "contig8030_8039_all_nodims": ["A_init_stride", "B_clear_contig_8030_8039", "C_fb_calc", "D_fb_contig_8030_8039", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "contig8030_8039_all_dim0_gameplayxy_tnddefaultwidthheight480i": ["A_init_stride", "B_clear_contig_8030_8039", "C_fb_calc", "D_fb_contig_8030_8039", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "contig8030_8039_all_dim0_frontbuf_gameplayxy_tnddefaultwidthheight480i": ["A_init_stride", "B_clear_contig_8030_8039", "C_fb_calc", "D_fb_contig_8030_8039", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetbuf_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "contig8030_8039_all_dim0_frontbuf_title640asset_gameplayxy_tnddefaultwidthheight480i": ["A_init_stride", "B_clear_contig_8030_8039", "C_fb_calc", "D_fb_contig_8030_8039", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_asset640_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "single8076_mem_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000"],
    "single8076_mem_f_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word"],
    "single8076_mem_g_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "G_mask_word"],
    "single8076_mem_fg_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word"],
    "single8076_mem_fg_h_origin_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_origin_bypass"],
    "single8076_mem_fg_h_width_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_width_vsync"],
    "single8076_mem_fg_h_scale_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_scale"],
    "single8076_mem_fg_h_width_scale_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_width_scale"],
    "single8076_mem_fg_h_origin_width_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_origin_width"],
    "single8076_mem_fg_h_origin_scale_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_origin_scale"],
    "single8076_all_nodims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "single8076_all_dim0": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "E_direct_dim0", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "single8076_all_dim1": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "E_direct_dim1", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "single8076_all_dims": ["A_single_stride_zero", "B_clear_single_8076A000", "C_single_offset_zero", "D_fb_single_8076A000", "E_direct_dims", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8060_8076_mem_nodims": ["A_split_load_two_globals", "B_clear_split_8060_8076", "C_split_select_global", "D_fb_split_8060_8076"],
    "split8060_8076_all_nodims": ["A_split_load_two_globals", "B_clear_split_8060_8076", "C_split_select_global", "D_fb_split_8060_8076", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_mem_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076"],
    "split8030_8076_mem_fg_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "F_vi_word", "G_mask_word"],
    "split8030_8076_mem_fg_h_width_scale_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "F_vi_word", "G_mask_word", "H_width_scale"],
    "split8030_8076_all_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_width480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_view_width_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_height480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_view_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_viewsize480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_view_width_480i", "I_gameplay_view_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_fullscreenview480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_fullscreen_view_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tndfullscreen480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_fullscreen_view_640x480", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultgeview480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_ge_view_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidth480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultheight480full480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_height_480_full_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaulttop480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_top_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaulttopzero480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_top_zero_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheighttopzero480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "I_gameplay_tnd_default_top_zero_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight480full480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "I_gameplay_tnd_default_height_480_full_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight480fulltopzero480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "I_gameplay_tnd_default_height_480_full_480i", "I_gameplay_tnd_default_top_zero_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_dim1width_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "E_direct_dim1_width640", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_dim1height_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "E_direct_dim1_height480", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_dim1_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "E_direct_dim1", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight_camerawidth480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "I_gameplay_tnd_camera_width_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight_cameraheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "I_gameplay_tnd_camera_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tnddefaultwidthheight_camerawidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "I_gameplay_tnd_camera_width_480i", "I_gameplay_tnd_camera_height_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tndcamerageview480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_camera_ge_view_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplayxy_tndgeview480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_ge_view_keep_camera_top_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_gameplay480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_viewport_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontgameplay480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_viewport_480i", "J_front_title_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontres_gameplay480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_viewport_480i", "J_front_resolution_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxy_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxy_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetbuf_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxybuf_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxybuf_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontzbuf_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_zbuffer_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontres_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_fronttitle_norectloop_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "J_front_layout_no_rectloop_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_rectloop_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_640x430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_tndrect430_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_764_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_tndrect480_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_764_crop480", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_tndrect509_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_764_full509", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_tndrect508src430_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_508_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_tndrect508src480_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_rectloop_tnd_stride_508_height480", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640draw_tndstride430": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "K_title_draw_ge480_target_tnd_stride_764_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640draw_tndsrc508height430": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "K_title_draw_ge480_target_tnd_stride_508_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640asset_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_asset640_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_title640asset_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_asset640_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_title640asset_gameplayxy_tnddefaultwidth480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_asset640_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_title640asset_skipfileselect_gameplayxy_tnddefaultwidth480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontzbuf_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_zbuffer_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxy_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxy_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxybuf_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxybuf_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontres_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontlayout_title640asset_skipfileselect_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "J_front_layout_no_rectloop_480i", "J_expanded_menu_resolution_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontlayout_title640asset_skipfileselect_postbloodskip_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "J_front_layout_no_rectloop_480i", "J_expanded_menu_resolution_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "M_skip_postblood_sniper_blitter", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontlayout_title640asset_skipfileselect_postbloodeyeskip_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "J_front_layout_no_rectloop_480i", "J_expanded_menu_resolution_480i", "K_title_draw_ge480_target_asset640_height430", "L_skip_file_select_backdrop", "M_skip_postblood_sniper_blitter", "N_skip_postblood_eye_backdrop", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontlayout_titletarget_stocksource_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "J_front_layout_no_rectloop_480i", "J_expanded_menu_resolution_480i", "K_title_draw_ge480_target_stock_source", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_titletarget_stocksource_gameplayxy_tnddefaultwidthheight480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_stock_source", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontbuf_titletarget_stocksource_gameplayxy_tnddefaultwidth480i_virtualfb": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global_virtual", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_480i", "J_front_visetbuf_480i", "K_title_draw_ge480_target_stock_source", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640draw_tndstride430_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_tnd_stride_764_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640draw_tndstride480_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_tnd_stride_764_height480", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_title640draw_tndstride508_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "K_title_draw_ge480_target_tnd_stride_764_height508", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxybuf_title640draw_tndstride430_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxybuf_480i", "K_title_draw_ge480_target_tnd_stride_764_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxybuf_title640draw_tndstride480_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxybuf_480i", "K_title_draw_ge480_target_tnd_stride_764_height480", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontxybuf_title640draw_tndstride508_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_visetxybuf_480i", "K_title_draw_ge480_target_tnd_stride_764_height508", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontres_title640draw_tndstride430_gameplayxy_tnddefaultwidthheight480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_xy_480i", "I_gameplay_tnd_default_width_height_480i", "J_front_resolution_480i", "K_title_draw_ge480_target_tnd_stride_764_height430", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontres_hlimit_gameplay480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_viewport_480i", "J_front_resolution_480i", "J_front_height_limit_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_frontres_expanded_gameplay480i": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "I_gameplay_viewport_480i", "J_front_resolution_480i", "J_expanded_menu_resolution_480i", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim1": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim1", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_dim1_width640": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "E_direct_dim1_width640", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dim0_dim1_height480": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dim0", "E_direct_dim1_height480", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_all_dims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "E_direct_dims", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8040_8076_mem_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076"],
    "split8040_8076_mem_f_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word"],
    "split8040_8076_mem_g_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "G_mask_word"],
    "split8040_8076_mem_h_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "H_pi_dma"],
    "split8040_8076_mem_fg_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word"],
    "split8040_8076_mem_fg_h_origin_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_origin_bypass"],
    "split8040_8076_mem_fg_h_width_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_width_vsync"],
    "split8040_8076_mem_fg_h_scale_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_scale"],
    "split8040_8076_mem_fg_h_width_scale_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_width_scale"],
    "split8040_8076_mem_fg_h_origin_width_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_origin_width"],
    "split8040_8076_mem_fg_h_origin_scale_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_origin_scale"],
    "split8040_8076_mem_fh_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "H_pi_dma"],
    "split8040_8076_mem_gh_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "G_mask_word", "H_pi_dma"],
    "split8040_8076_all_nodims": ["A_split_load_two_globals", "B_clear_split_8040_8076", "C_split_select_global", "D_fb_split_8040_8076", "F_vi_word", "G_mask_word", "H_pi_dma"],
}


def read(path):
    return Path(path).read_bytes()


def write(path, data):
    Path(path).write_bytes(data)


def md5(data):
    return hashlib.md5(data).hexdigest()


def byte_diff_count(a, b):
    return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))


def inflate_ge1172(rom, offset=GE_1172_OFFSET):
    if rom[offset:offset + 2] != b"\x11\x72":
        raise ValueError(f"no 1172 marker at 0x{offset:X}")
    payload = rom[offset + 2:]
    decomp = zlib.decompressobj(-15)
    raw = decomp.decompress(payload)
    raw += decomp.flush()
    consumed = len(payload) - len(decomp.unused_data) + 2
    return raw, consumed


def pack_ge1172(raw, zopfli_iterations=15):
    comp = zlib.compressobj(level=9, wbits=-15)
    payload = comp.compress(raw) + comp.flush()
    try:
        import zopfli.zlib

        zopfli_payload = zopfli.zlib.compress(raw, numiterations=zopfli_iterations)[2:-4]
        if len(zopfli_payload) < len(payload):
            payload = zopfli_payload
    except Exception:
        pass

    out_len = 2 + len(payload)
    if out_len % 8:
        out_len += 8 - (out_len % 8)
    out = bytearray(out_len)
    out[0:2] = b"\x11\x72"
    out[2:2 + len(payload)] = payload
    return bytes(out)


def rol(value, bits):
    bits &= 31
    return ((value << bits) | (value >> (32 - bits))) & 0xFFFFFFFF


def calc_n64_crc_6102(rom):
    t1 = t2 = t3 = t4 = t5 = t6 = CRC_6102_SEED
    for off in range(CRC_BOOT_START, CRC_BOOT_END, 4):
        d = int.from_bytes(rom[off:off + 4], "big")
        if t6 + d > 0xFFFFFFFF:
            t4 = (t4 + 1) & 0xFFFFFFFF
        t6 = (t6 + d) & 0xFFFFFFFF
        t3 ^= d
        r = rol(d, d & 0x1F)
        t5 = (t5 + r) & 0xFFFFFFFF
        if t2 > d:
            t2 ^= r
        else:
            t2 ^= t6 ^ d
        t1 = (t1 + (t5 ^ d)) & 0xFFFFFFFF
    return (t6 ^ t4 ^ t3) & 0xFFFFFFFF, (t5 ^ t2 ^ t1) & 0xFFFFFFFF


def update_n64_crc_6102(rom):
    crc1, crc2 = calc_n64_crc_6102(rom)
    rom[0x10:0x14] = crc1.to_bytes(4, "big")
    rom[0x14:0x18] = crc2.to_bytes(4, "big")
    return crc1, crc2


def apply_main_ranges(tnd_raw, ge_raw, ranges):
    out = bytearray(tnd_raw)
    report = []
    for start, end, note in ranges:
        before = bytes(out[start:end])
        out[start:end] = ge_raw[start:end]
        report.append({
            "start": f"0x{start:X}",
            "end": f"0x{end:X}",
            "len": end - start,
            "note": note,
            "changed_bytes": byte_diff_count(before, ge_raw[start:end]),
        })
    return bytes(out), report


def apply_direct_words(rom, profile):
    report = []
    for group in DIRECT_PATCH_PROFILES[profile]:
        for off, value, note in DIRECT_PATCH_GROUPS[group]:
            old = int.from_bytes(rom[off:off + 4], "big")
            rom[off:off + 4] = value.to_bytes(4, "big")
            report.append({
                "group": group,
                "offset": f"0x{off:X}",
                "old": f"0x{old:08X}",
                "new": f"0x{value:08X}",
                "note": note,
            })
    return report


def build(args):
    base = bytearray(read(args.base_rom))
    ge = read(args.ge480i_rom)
    _base_raw, slot_len = inflate_ge1172(base, args.offset)
    ge_raw, _ = inflate_ge1172(ge, args.offset)
    tnd_raw, _ = inflate_ge1172(base, args.offset)

    ranges = MAIN_RANGE_SETS[args.variant]
    patched_raw, main_report = apply_main_ranges(tnd_raw, ge_raw, ranges)
    packed_len = 0
    if ranges:
        packed = pack_ge1172(patched_raw, args.zopfli_iterations)
        if len(packed) > slot_len:
            raise ValueError(f"packed stream too large: 0x{len(packed):X} > 0x{slot_len:X}")

        base[args.offset:args.offset + slot_len] = b"\x00" * slot_len
        base[args.offset:args.offset + len(packed)] = packed
        packed_len = len(packed)
    direct_report = apply_direct_words(base, args.direct_profile)
    crc1, crc2 = update_n64_crc_6102(base)
    write(args.out_rom, base)

    verify_raw, verify_consumed = inflate_ge1172(base, args.offset)
    report = {
        "base_rom": args.base_rom,
        "ge480i_rom": args.ge480i_rom,
        "out_rom": args.out_rom,
        "variant": args.variant,
        "direct_profile": args.direct_profile,
        "out_md5": md5(base),
        "header_crc": f"{crc1:08X}{crc2:08X}",
        "main_raw_md5": md5(patched_raw),
        "verify_main_raw_md5": md5(verify_raw),
        "slot_len": f"0x{slot_len:X}",
        "packed_len": f"0x{packed_len:X}",
        "zopfli_iterations": args.zopfli_iterations,
        "verify_consumed": f"0x{verify_consumed:X}",
        "main_changed_bytes_from_tnd": byte_diff_count(tnd_raw, patched_raw),
        "main_ranges": main_report,
        "direct_word_patches": direct_report,
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-rom", default="BASELINE_TND64_Expanded_direct_from_stock.z64")
    parser.add_argument("--ge480i-rom", default="BASELINE_GE_480i_direct_from_stock.z64")
    parser.add_argument("--out-rom", default="TND64_480i_mem_tables_candidate.z64")
    parser.add_argument("--report", default="parallel_diag/tnd480i_mem_tables_candidate_report.json")
    parser.add_argument("--offset", type=lambda x: int(x, 0), default=GE_1172_OFFSET)
    parser.add_argument("--variant", choices=sorted(MAIN_RANGE_SETS), default="all")
    parser.add_argument("--direct-profile", choices=sorted(DIRECT_PATCH_PROFILES), default="mem_dims")
    parser.add_argument("--zopfli-iterations", type=int, default=15)
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
