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
    "E_direct_dims": [
    (0x4F354, 0x028001E0, "direct render dimensions table 0"),
    (0x4F35C, 0x028001E0, "direct render dimensions table 1"),
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
    "mem_nodims": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn"],
    "mem_dims": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn", "E_direct_dims"],
    "other": ["F_vi_word", "G_mask_word", "H_pi_dma"],
    "all_nodims": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "all": ["A_init_stride", "B_alloc_reserve", "C_fb_calc", "D_mem_fn", "E_direct_dims", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "fixed8040_mem_nodims": ["A_init_stride", "B_clear_fixed_8040", "C_fb_calc", "D_fb_fixed_8040"],
    "fixed8040_all_nodims": ["A_init_stride", "B_clear_fixed_8040", "C_fb_calc", "D_fb_fixed_8040", "F_vi_word", "G_mask_word", "H_pi_dma"],
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
    "split8060_8076_mem_nodims": ["A_split_load_two_globals", "B_clear_split_8060_8076", "C_split_select_global", "D_fb_split_8060_8076"],
    "split8060_8076_all_nodims": ["A_split_load_two_globals", "B_clear_split_8060_8076", "C_split_select_global", "D_fb_split_8060_8076", "F_vi_word", "G_mask_word", "H_pi_dma"],
    "split8030_8076_mem_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076"],
    "split8030_8076_mem_fg_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "F_vi_word", "G_mask_word"],
    "split8030_8076_mem_fg_h_width_scale_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "F_vi_word", "G_mask_word", "H_width_scale"],
    "split8030_8076_all_nodims": ["A_split_load_two_globals", "B_clear_split_8030_8076", "C_split_select_global", "D_fb_split_8030_8076", "F_vi_word", "G_mask_word", "H_pi_dma"],
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


def pack_ge1172(raw):
    comp = zlib.compressobj(level=9, wbits=-15)
    payload = comp.compress(raw) + comp.flush()
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
        packed = pack_ge1172(patched_raw)
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
    args = parser.parse_args()
    build(args)


if __name__ == "__main__":
    main()
