# TND64 480i Patch-Site Audit

Generated from local ROMs only. No hardware upload was performed.

## Conclusions

- `TND64_enh480i_core_no_menu_pigz.z64` contains the compressed-main core table changes, but it leaves the direct VI/framebuffer boot-code sites at TND stock values. That matches the observed behavior: it can boot without proving true 480i output.
- `single FG+width+scale` has the single-high framebuffer layout plus GE 480i width/vsync and scale writes, but omits the origin/control-flow bypass at `0x19978/0x19980`.
- `single all` and the new `single FG+origin*` builds add that origin branch family while keeping the safer `0x8076A000` single-buffer memory placement.
- The `+ dims` builds also patch the two direct gameplay dimension words at `0x4F354` and `0x4F35C` from `320x240`/`440x330` to `640x480`; this is the likely missing piece behind the aliased Bond-hand result from the no-dims single-all hardware test.
- `split8030 all + dims` is the double-buffer fallback that avoids both the earlier `0x80400000` real-hardware failure point and the known `0x8070xxxx` TND references while also applying the direct dimension words.

## ROM Inventory

| Label | File | MD5 |
|---|---|---|
| GE stock | `artifacts\roms\GoldenEye 007 (USA).z64` | `70c525880240c1e838b8b1be35666c3b` |
| GE 480i | `artifacts\roms\BASELINE_GE_480i_direct_from_stock.z64` | `1ff9bb4987e83dc85b0d314545a6025f` |
| TND base | `artifacts\roms\BASELINE_TND64_Expanded_direct_from_stock.z64` | `1ee22dd1d70443f5e4766d4238756949` |
| TND tables only | `artifacts\roms\TND64_enh480i_core_no_menu_pigz.z64` | `5e022639fe3aab5e2aa8a209339621d1` |
| single all | `artifacts\generated\TND64_480i_single8076_all_core_no_menu.z64` | `3c6306b06ad9d52121ccc6817038a525` |
| single all + dims | `artifacts\generated\TND64_480i_single8076_all_dims_core_no_menu.z64` | `8f4c7fdf524ec1c7f4fc63223a8b386c` |
| split8030 all | `artifacts\generated\TND64_480i_split8030_8076_all_core_no_menu.z64` | `6464d1b85aa7fc60d5a6fbf36fa71bf7` |
| split8030 all + dims | `artifacts\generated\TND64_480i_split8030_8076_all_dims_core_no_menu.z64` | `cce443d766bd681a511f7d18bb95b657` |

## Portable GE 480i Byte Runs

`GE stock != GE 480i` and `TND base == GE stock` before the compressed main: 18 runs, 54 bytes.

| Start | End | Bytes |
|---:|---:|---:|
| `0x003D33` | `0x003D34` | 1 |
| `0x00441F` | `0x004420` | 1 |
| `0x0046C8` | `0x0046D1` | 9 |
| `0x0046D2` | `0x0046D8` | 6 |
| `0x0046D9` | `0x0046DA` | 1 |
| `0x0046DB` | `0x0046E0` | 5 |
| `0x0046E9` | `0x0046EC` | 3 |
| `0x006587` | `0x006588` | 1 |
| `0x00658F` | `0x006590` | 1 |
| `0x0104DE` | `0x0104DF` | 1 |
| `0x019978` | `0x01997C` | 4 |
| `0x019980` | `0x019986` | 6 |
| `0x019987` | `0x019988` | 1 |
| `0x0199B4` | `0x0199B7` | 3 |
| `0x0199D0` | `0x0199D2` | 2 |
| `0x019A24` | `0x019A28` | 4 |
| `0x019A61` | `0x019A62` | 1 |
| `0x019A64` | `0x019A68` | 4 |

## Direct Word Sites

| Offset | Groups | TND base | GE 480i | Single all | Single all + dims | Split8030 all | Split8030 all + dims |
|---:|---|---|---|---|---|---|---|
| `0x003C8C` | A_init_stride, A_single_stride_zero, A_split_load_two_globals | `3C010002` lui $at, 2 | `3C010009` lui $at, 9 | `00000825` move $at, $zero | `00000825` move $at, $zero | `8CC94180` lw $t1, 0x4180($a2) | `8CC94180` lw $t1, 0x4180($a2) |
| `0x003C90` | A_init_stride, A_single_stride_zero, A_split_load_two_globals | `24215800` addiu $at, $at, 0x5800 | `24216000` addiu $at, $at, 0x6000 | `00000000` nop | `00000000` nop | `01214825` or $t1, $t1, $at | `01214825` or $t1, $t1, $at |
| `0x003C94` | A_split_load_two_globals | `01214821` addu $t1, $t1, $at | `01214821` addu $t1, $t1, $at | `01214821` addu $t1, $t1, $at | `01214821` addu $t1, $t1, $at | `01214826` xor $t1, $t1, $at | `01214826` xor $t1, $t1, $at |
| `0x003D24` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `AFBFFFFC` sw $ra, -4($sp) | `AFBFFFFC` sw $ra, -4($sp) | `AFBFFFFC` sw $ra, -4($sp) | `AFBFFFFC` sw $ra, -4($sp) | `AFBFFFFC` sw $ra, -4($sp) | `AFBFFFFC` sw $ra, -4($sp) |
| `0x003D28` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0FC348E0` jal 0xf0d2380 | `0FC348E0` jal 0xf0d2380 | `0FC348E0` jal 0xf0d2380 | `0FC348E0` jal 0xf0d2380 | `0FC348E0` jal 0xf0d2380 | `0FC348E0` jal 0xf0d2380 |
| `0x003D2C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `27BDFFE8` addiu $sp, $sp, -0x18 | `27BDFFE8` addiu $sp, $sp, -0x18 | `27BDFFE8` addiu $sp, $sp, -0x18 | `27BDFFE8` addiu $sp, $sp, -0x18 | `27BDFFE8` addiu $sp, $sp, -0x18 | `27BDFFE8` addiu $sp, $sp, -0x18 |
| `0x003D30` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `3C058000` lui $a1, 0x8000 | `3C048080` lui $a0, 0x8080 | `3C048076` lui $a0, 0x8076 | `3C048076` lui $a0, 0x8076 | `3C048030` lui $a0, 0x8030 | `3C048030` lui $a0, 0x8030 |
| `0x003D34` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `8CA40318` lw $a0, 0x318($a1) | `00000000` nop | `3484A000` ori $a0, $a0, 0xa000 | `3484A000` ori $a0, $a0, 0xa000 | `00000000` nop | `00000000` nop |
| `0x003D38` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00852025` or $a0, $a0, $a1 | `00000000` nop | `00000000` nop | `00000000` nop | `3C050009` lui $a1, 9 | `3C050009` lui $a1, 9 |
| `0x003D3C` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `3C050004` lui $a1, 4 | `3C050012` lui $a1, 0x12 | `3C050009` lui $a1, 9 | `3C050009` lui $a1, 9 | `34A56000` ori $a1, $a1, 0x6000 | `34A56000` ori $a1, $a1, 0x6000 |
| `0x003D40` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `34A5B000` ori $a1, $a1, 0xb000 | `34A5C000` ori $a1, $a1, 0xc000 | `34A56000` ori $a1, $a1, 0x6000 | `34A56000` ori $a1, $a1, 0x6000 | `0C005F10` jal 0x17c40 | `0C005F10` jal 0x17c40 |
| `0x003D44` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0C005F10` jal 0x17c40 | `0C005F10` jal 0x17c40 | `0C005F10` jal 0x17c40 | `0C005F10` jal 0x17c40 | `00000000` nop | `00000000` nop |
| `0x003D48` | B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00852023` subu $a0, $a0, $a1 | `00852023` subu $a0, $a0, $a1 | `00000000` nop | `00000000` nop | `3C048076` lui $a0, 0x8076 | `3C048076` lui $a0, 0x8076 |
| `0x003D4C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `8FBF0014` lw $ra, 0x14($sp) | `8FBF0014` lw $ra, 0x14($sp) | `8FBF0014` lw $ra, 0x14($sp) | `8FBF0014` lw $ra, 0x14($sp) | `3484A000` ori $a0, $a0, 0xa000 | `3484A000` ori $a0, $a0, 0xa000 |
| `0x003D50` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `03E00008` jr $ra | `03E00008` jr $ra | `03E00008` jr $ra | `03E00008` jr $ra | `3C050009` lui $a1, 9 | `3C050009` lui $a1, 9 |
| `0x003D54` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `27BD0018` addiu $sp, $sp, 0x18 | `27BD0018` addiu $sp, $sp, 0x18 | `27BD0018` addiu $sp, $sp, 0x18 | `27BD0018` addiu $sp, $sp, 0x18 | `34A56000` ori $a1, $a1, 0x6000 | `34A56000` ori $a1, $a1, 0x6000 |
| `0x003D58` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `0C005F10` jal 0x17c40 | `0C005F10` jal 0x17c40 |
| `0x003D5C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D60` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `8FBF0014` lw $ra, 0x14($sp) | `8FBF0014` lw $ra, 0x14($sp) |
| `0x003D64` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `03E00008` jr $ra | `03E00008` jr $ra |
| `0x003D68` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `27BD0018` addiu $sp, $sp, 0x18 | `27BD0018` addiu $sp, $sp, 0x18 |
| `0x003D6C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D70` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D74` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D78` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D7C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D80` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D84` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D88` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x003D8C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x00441C` | F_vi_word | `00187840` sll $t7, $t8, 1 | `00187880` sll $t7, $t8, 2 | `00187880` sll $t7, $t8, 2 | `00187880` sll $t7, $t8, 2 | `00187880` sll $t7, $t8, 2 | `00187880` sll $t7, $t8, 2 |
| `0x0046B4` | C_split_select_global | `3C048002` lui $a0, 0x8002 | `3C048002` lui $a0, 0x8002 | `3C048002` lui $a0, 0x8002 | `3C048002` lui $a0, 0x8002 | `3C038006` lui $v1, 0x8006 | `3C038006` lui $v1, 0x8006 |
| `0x0046B8` | C_split_select_global | `0C00012B` jal 0x4ac | `0C00012B` jal 0x4ac | `0C00012B` jal 0x4ac | `0C00012B` jal 0x4ac | `90780879` lbu $t8, 0x879($v1) | `90780879` lbu $t8, 0x879($v1) |
| `0x0046BC` | C_split_select_global | `8C84417C` lw $a0, 0x417c($a0) | `8C84417C` lw $a0, 0x417c($a0) | `8C84417C` lw $a0, 0x417c($a0) | `8C84417C` lw $a0, 0x417c($a0) | `0018C080` sll $t8, $t8, 2 | `0018C080` sll $t8, $t8, 2 |
| `0x0046C0` | C_split_select_global | `3C038006` lui $v1, 0x8006 | `3C038006` lui $v1, 0x8006 | `3C038006` lui $v1, 0x8006 | `3C038006` lui $v1, 0x8006 | `3C048002` lui $a0, 0x8002 | `3C048002` lui $a0, 0x8002 |
| `0x0046C4` | C_split_select_global | `90780879` lbu $t8, 0x879($v1) | `90780879` lbu $t8, 0x879($v1) | `90780879` lbu $t8, 0x879($v1) | `90780879` lbu $t8, 0x879($v1) | `00982021` addu $a0, $a0, $t8 | `00982021` addu $a0, $a0, $t8 |
| `0x0046C8` | C_fb_calc, C_single_offset_zero, C_split_select_global | `00187880` sll $t7, $t8, 2 | `3C0F0009` lui $t7, 9 | `00007825` move $t7, $zero | `00007825` move $t7, $zero | `0C00012B` jal 0x4ac | `0C00012B` jal 0x4ac |
| `0x0046CC` | C_fb_calc, C_single_offset_zero, C_split_select_global | `01F87821` addu $t7, $t7, $t8 | `35EF6000` ori $t7, $t7, 0x6000 | `00000000` nop | `00000000` nop | `8C84417C` lw $a0, 0x417c($a0) | `8C84417C` lw $a0, 0x417c($a0) |
| `0x0046D0` | C_fb_calc, C_single_offset_zero, C_split_select_global | `000F7880` sll $t7, $t7, 2 | `030F0018` mult $t8, $t7 | `00000000` nop | `00000000` nop | `3C188002` lui $t8, 0x8002 | `3C188002` lui $t8, 0x8002 |
| `0x0046D4` | C_fb_calc, C_single_offset_zero, C_split_select_global | `01F87823` subu $t7, $t7, $t8 | `00000000` nop | `00000000` nop | `00000000` nop | `8F1832A8` lw $t8, 0x32a8($t8) | `8F1832A8` lw $t8, 0x32a8($t8) |
| `0x0046D8` | C_fb_calc, C_single_offset_zero, C_split_select_global | `000F7880` sll $t7, $t7, 2 | `00007812` mflo $t7 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x0046DC` | C_fb_calc, C_single_offset_zero, C_split_select_global | `01F87823` subu $t7, $t7, $t8 | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x0046E0` | C_split_select_global | `3C188002` lui $t8, 0x8002 | `3C188002` lui $t8, 0x8002 | `3C188002` lui $t8, 0x8002 | `3C188002` lui $t8, 0x8002 | `00000000` nop | `00000000` nop |
| `0x0046E4` | C_split_select_global | `8F1832A8` lw $t8, 0x32a8($t8) | `8F1832A8` lw $t8, 0x32a8($t8) | `8F1832A8` lw $t8, 0x32a8($t8) | `8F1832A8` lw $t8, 0x32a8($t8) | `00000000` nop | `00000000` nop |
| `0x0046E8` | C_fb_calc, C_single_offset_zero, C_split_select_global | `000F7AC0` sll $t7, $t7, 0xb | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x0046EC` | C_split_select_global | `01E2C821` addu $t9, $t7, $v0 | `01E2C821` addu $t9, $t7, $v0 | `01E2C821` addu $t9, $t7, $v0 | `01E2C821` addu $t9, $t7, $v0 | `0040C825` move $t9, $v0 | `0040C825` move $t9, $v0 |
| `0x0046F0` | C_split_select_global | `AF190028` sw $t9, 0x28($t8) | `AF190028` sw $t9, 0x28($t8) | `AF190028` sw $t9, 0x28($t8) | `AF190028` sw $t9, 0x28($t8) | `AF190028` sw $t9, 0x28($t8) | `AF190028` sw $t9, 0x28($t8) |
| `0x006584` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `3C048000` lui $a0, 0x8000 | `3C048080` lui $a0, 0x8080 | `3C048076` lui $a0, 0x8076 | `3C048076` lui $a0, 0x8076 | `3C048030` lui $a0, 0x8030 | `3C048030` lui $a0, 0x8030 |
| `0x006588` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `8C840318` lw $a0, 0x318($a0) | `00000000` nop | `3484A000` ori $a0, $a0, 0xa000 | `3484A000` ori $a0, $a0, 0xa000 | `34840000` ori $a0, $a0, 0 | `34840000` ori $a0, $a0, 0 |
| `0x00658C` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `3C020002` lui $v0, 2 | `3C020009` lui $v0, 9 | `00802825` move $a1, $a0 | `00802825` move $a1, $a0 | `3C058076` lui $a1, 0x8076 | `3C058076` lui $a1, 0x8076 |
| `0x006590` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `24425800` addiu $v0, $v0, 0x5800 | `24426000` addiu $v0, $v0, 0x6000 | `3C02A000` lui $v0, 0xa000 | `3C02A000` lui $v0, 0xa000 | `34A5A000` ori $a1, $a1, 0xa000 | `34A5A000` ori $a1, $a1, 0xa000 |
| `0x006594` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `00822823` subu $a1, $a0, $v0 | `00822823` subu $a1, $a0, $v0 | `00827025` or $t6, $a0, $v0 | `00827025` or $t6, $a0, $v0 | `3C02A000` lui $v0, 0xa000 | `3C02A000` lui $v0, 0xa000 |
| `0x006598` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `00A22023` subu $a0, $a1, $v0 | `00A22023` subu $a0, $a1, $v0 | `3C018002` lui $at, 0x8002 | `3C018002` lui $at, 0x8002 | `00827025` or $t6, $a0, $v0 | `00827025` or $t6, $a0, $v0 |
| `0x00659C` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `3C02A000` lui $v0, 0xa000 | `3C02A000` lui $v0, 0xa000 | `AC2E417C` sw $t6, 0x417c($at) | `AC2E417C` sw $t6, 0x417c($at) | `3C018002` lui $at, 0x8002 | `3C018002` lui $at, 0x8002 |
| `0x0065A0` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `00827025` or $t6, $a0, $v0 | `00827025` or $t6, $a0, $v0 | `00A27825` or $t7, $a1, $v0 | `00A27825` or $t7, $a1, $v0 | `AC2E417C` sw $t6, 0x417c($at) | `AC2E417C` sw $t6, 0x417c($at) |
| `0x0065A4` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `3C018002` lui $at, 0x8002 | `3C018002` lui $at, 0x8002 | `03E00008` jr $ra | `03E00008` jr $ra | `00A27825` or $t7, $a1, $v0 | `00A27825` or $t7, $a1, $v0 |
| `0x0065A8` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `AC2E417C` sw $t6, 0x417c($at) | `AC2E417C` sw $t6, 0x417c($at) | `AC2F4180` sw $t7, 0x4180($at) | `AC2F4180` sw $t7, 0x4180($at) | `03E00008` jr $ra | `03E00008` jr $ra |
| `0x0065AC` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `00A27825` or $t7, $a1, $v0 | `00A27825` or $t7, $a1, $v0 | `00000000` nop | `00000000` nop | `AC2F4180` sw $t7, 0x4180($at) | `AC2F4180` sw $t7, 0x4180($at) |
| `0x0065B0` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `03E00008` jr $ra | `03E00008` jr $ra | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x0065B4` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `AC2F4180` sw $t7, 0x4180($at) | `AC2F4180` sw $t7, 0x4180($at) | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x0104DC` | G_mask_word | `2401FCFF` addiu $at, $zero, -0x301 | `2401FFFF` addiu $at, $zero, -1 | `2401FFFF` addiu $at, $zero, -1 | `2401FFFF` addiu $at, $zero, -1 | `2401FFFF` addiu $at, $zero, -1 | `2401FFFF` addiu $at, $zero, -1 |
| `0x019978` | H_origin_bypass, H_origin_scale, H_origin_width, H_pi_dma | `00000000` nop | `3C09A440` lui $t1, 0xa440 | `3C09A440` lui $t1, 0xa440 | `3C09A440` lui $t1, 0xa440 | `3C09A440` lui $t1, 0xa440 | `3C09A440` lui $t1, 0xa440 |
| `0x019980` | H_origin_bypass, H_origin_scale, H_origin_width, H_pi_dma | `3C0103FF` lui $at, 0x3ff | `10000006` b 0x1999c | `10000006` b 0x1999c | `10000006` b 0x1999c | `10000006` b 0x1999c | `10000006` b 0x1999c |
| `0x019984` | H_origin_bypass, H_origin_scale, H_origin_width, H_pi_dma | `8E240004` lw $a0, 4($s1) | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop | `00000000` nop |
| `0x0199B4` | H_origin_width, H_pi_dma, H_width_scale, H_width_vsync | `3C18A440` lui $t8, 0xa440 | `000C6040` sll $t4, $t4, 1 | `000C6040` sll $t4, $t4, 1 | `000C6040` sll $t4, $t4, 1 | `000C6040` sll $t4, $t4, 1 | `000C6040` sll $t4, $t4, 1 |
| `0x0199D0` | H_origin_width, H_pi_dma, H_width_scale, H_width_vsync | `AF0E0018` sw $t6, 0x18($t8) | `ADEE0018` sw $t6, 0x18($t7) | `ADEE0018` sw $t6, 0x18($t7) | `ADEE0018` sw $t6, 0x18($t7) | `ADEE0018` sw $t6, 0x18($t7) | `ADEE0018` sw $t6, 0x18($t7) |
| `0x019A24` | H_origin_scale, H_pi_dma, H_scale, H_width_scale | `3C0AA440` lui $t2, 0xa440 | `8E2B002C` lw $t3, 0x2c($s1) | `8E2B002C` lw $t3, 0x2c($s1) | `8E2B002C` lw $t3, 0x2c($s1) | `8E2B002C` lw $t3, 0x2c($s1) | `8E2B002C` lw $t3, 0x2c($s1) |
| `0x019A60` | H_origin_scale, H_pi_dma, H_scale, H_width_scale | `AD490030` sw $t1, 0x30($t2) | `AD890030` sw $t1, 0x30($t4) | `AD890030` sw $t1, 0x30($t4) | `AD890030` sw $t1, 0x30($t4) | `AD890030` sw $t1, 0x30($t4) | `AD890030` sw $t1, 0x30($t4) |
| `0x019A64` | H_origin_scale, H_pi_dma, H_scale, H_width_scale | `8E2B002C` lw $t3, 0x2c($s1) | `000B5842` srl $t3, $t3, 1 | `000B5842` srl $t3, $t3, 1 | `000B5842` srl $t3, $t3, 1 | `000B5842` srl $t3, $t3, 1 | `000B5842` srl $t3, $t3, 1 |
| `0x04F354` | E_direct_dims | `014000F0` tge $t2, $zero, 3 | `028001E0`  | `014000F0` tge $t2, $zero, 3 | `028001E0`  | `014000F0` tge $t2, $zero, 3 | `028001E0`  |
| `0x04F35C` | E_direct_dims | `01B8014A`  | `028001E0`  | `01B8014A`  | `028001E0`  | `01B8014A`  | `028001E0`  |

## Profile Checks

| ROM | Profile | Expected words | Mismatches |
|---|---|---:|---:|
| single all | `single8076_all_nodims` | 38 | 0 |
| single all + dims | `single8076_all_dims` | 40 | 0 |
| split8030 all | `split8030_8076_all_nodims` | 69 | 0 |
| split8030 all + dims | `split8030_8076_all_dims` | 71 | 0 |

## Main Table Ranges

| ROM | Main MD5 | Core ranges equal GE 480i | Menu ranges equal GE 480i |
|---|---|---:|---:|
| GE stock | `055525d9087f953d43d80639773b4291` | 0/4 | 0/2 |
| GE 480i | `b374298c9253148eb1e3a86a971a79b1` | 4/4 | 2/2 |
| TND base | `22272695451cab0af3b1075c917fc4de` | 0/4 | 0/2 |
| TND tables only | `b77ac94fd19847299613d6ab600047a2` | 4/4 | 0/2 |
| single all | `b77ac94fd19847299613d6ab600047a2` | 4/4 | 0/2 |
| single all + dims | `b77ac94fd19847299613d6ab600047a2` | 4/4 | 0/2 |
| split8030 all | `b77ac94fd19847299613d6ab600047a2` | 4/4 | 0/2 |
| split8030 all + dims | `b77ac94fd19847299613d6ab600047a2` | 4/4 | 0/2 |

Full machine-readable details are in `reports\patch_site_audit.json`.
