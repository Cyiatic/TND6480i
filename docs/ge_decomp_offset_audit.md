# GE Decomp Offset Audit

Decomp root: `C:\Users\codex\Documents\n64\007-decomp\src`

This maps TND6480i direct patch offsets to comments in the local GoldenEye decomp. A blank source match means the offset is not represented by a first-field ROM/source-offset comment in that checkout.

## High-Risk Findings

- `0x0BB730` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15226`, but the comment word `0x00290821` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB740` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15231`, but the comment word `0x10000024` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB754` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15237`, but the comment word `0x144A000A` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB764` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15241`, but the comment word `0x00000000` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB790` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15255`, but the comment word `0x8E0B000C` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB7A4` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15260`, but the comment word `0x8E050008` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB7C0` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15271`, but the comment word `0x10000004` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB7D4` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15280`, but the comment word `0x8E020000` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB7DC` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15282`, but the comment word `0x5441FFD1` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.
- `0x0BB7E0` (I_gameplay_viewport_480i) has a same-offset decomp comment at `bondview.c:15283`, but the comment word `0x2C410007` does not match the GE stock ROM word. Treat that decomp line as a version/context collision.

## Offset Table

| Offset | Groups | GE stock | GE 480i | TND base | Decomp source matches |
|---:|---|---|---|---|---|
| `0x003C8C` | A_init_stride, A_single_stride_zero, A_split_load_two_globals | `0x3C058006` lui $a1, 0x8006 | `0x3C010009` lui $at, 9 | `0x3C010002` lui $at, 2 | `fr.c:1272` mismatch  `sw    $at, -8($t7)` |
| `0x003C90` | A_init_stride, A_single_stride_zero, A_split_load_two_globals | `0x00007812` mflo $t7 | `0x24216000` addiu $at, $at, 0x6000 | `0x24215800` addiu $at, $at, 0x5800 | `fr.c:1273` mismatch  `lw    $at, -4($t6)` |
| `0x003C94` | A_split_load_two_globals | `0x3C068002` lui $a2, 0x8002 | `0x01214821` addu $t1, $t1, $at | `0x01214821` addu $t1, $t1, $at | `fr.c:1274` mismatch  `bne   $t6, $t8, .L70003078` |
| `0x003D24` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x27BDFFE8` addiu $sp, $sp, -0x18 | `0xAFBFFFFC` sw $ra, -4($sp) | `0xAFBFFFFC` sw $ra, -4($sp) | `fr.c:1313` mismatch  `move  $t1, $zero` |
| `0x003D28` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xAFBF0014` sw $ra, 0x14($sp) | `0x0FC348E0` jal 0xf0d2380 | `0x0FC348E0` jal 0xf0d2380 | `fr.c:1314` mismatch  `sll   $t6, $t9, 0xa` |
| `0x003D2C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x0FC348E0` jal 0xf0d2380 | `0x27BDFFE8` addiu $sp, $sp, -0x18 | `0x27BDFFE8` addiu $sp, $sp, -0x18 | `fr.c:1315` mismatch  `div   $zero, $t6, $at` |
| `0x003D30` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x00000000` nop | `0x3C048080` lui $a0, 0x8080 | `0x3C058000` lui $a1, 0x8000 | `fr.c:1316` mismatch  `mflo  $t8` |
| `0x003D34` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x3C070002` lui $a3, 2 | `0x00000000` nop | `0x8CA40318` lw $a0, 0x318($a1) | `fr.c:1317` mismatch  `sw    $t8, 0x20($a0)` |
| `0x003D38` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x3C06803E` lui $a2, 0x803e | `0x00000000` nop | `0x00852025` or $a0, $a0, $a1 | `fr.c:1318` mismatch  `lh    $a1, 0x1a($a3)` |
| `0x003D3C` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x3C05803B` lui $a1, 0x803b | `0x3C050012` lui $a1, 0x12 | `0x3C050004` lui $a1, 4 | `fr.c:1319` mismatch  `bne   $t3, $a1, .L7000314C` |
| `0x003D40` | B_alloc_reserve, B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x24A55000` addiu $a1, $a1, 0x5000 | `0x34A5C000` ori $a1, $a1, 0xc000 | `0x34A5B000` ori $a1, $a1, 0xb000 | `fr.c:1320` mismatch  `sll   $t7, $a1, 0xb` |
| `0x003D44` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x24C6A800` addiu $a2, $a2, -0x5800 | `0x0C005F10` jal 0x17c40 | `0x0C005F10` jal 0x17c40 | `fr.c:1321` mismatch  `b     .L7000314C` |
| `0x003D48` | B_clear_fixed_8040, B_clear_single_8076A000, B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x34E75800` ori $a3, $a3, 0x5800 | `0x00852023` subu $a0, $a0, $a1 | `0x00852023` subu $a0, $a0, $a1 | `fr.c:1322` mismatch  `li    $v0, 28` |
| `0x003D4C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x00002025` move $a0, $zero | `0x8FBF0014` lw $ra, 0x14($sp) | `0x8FBF0014` lw $ra, 0x14($sp) | `fr.c:1324` mismatch  `addiu $t9, $v0, 0x220` |
| `0x003D50` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x00A41021` addu $v0, $a1, $a0 | `0x03E00008` jr $ra | `0x03E00008` jr $ra | `fr.c:1325` mismatch  `div   $zero, $t7, $t9` |
| `0x003D54` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0400000` sb $zero, ($v0) | `0x27BD0018` addiu $sp, $sp, 0x18 | `0x27BD0018` addiu $sp, $sp, 0x18 | `fr.c:1326` mismatch  `mflo  $t6` |
| `0x003D58` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x00C41821` addu $v1, $a2, $a0 | `0x00000000` nop | `0x00000000` nop | `fr.c:1327` mismatch  `sw    $t6, 0x2c($a0)` |
| `0x003D5C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0600000` sb $zero, ($v1) | `0x00000000` nop | `0x00000000` nop | `fr.c:1328` mismatch  `lh    $a1, 0x1a($a3)` |
| `0x003D60` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0400001` sb $zero, 1($v0) | `0x00000000` nop | `0x00000000` nop | `fr.c:1329` mismatch  `bnez  $t9, .L7000316C` |
| `0x003D64` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0600001` sb $zero, 1($v1) | `0x00000000` nop | `0x00000000` nop | `fr.c:1330` mismatch  `nop` |
| `0x003D68` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0400002` sb $zero, 2($v0) | `0x00000000` nop | `0x00000000` nop | `fr.c:1331` mismatch  `break 7` |
| `0x003D6C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0600002` sb $zero, 2($v1) | `0x00000000` nop | `0x00000000` nop | `fr.c:1333` mismatch  `li    $at, -1` |
| `0x003D70` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0400003` sb $zero, 3($v0) | `0x00000000` nop | `0x00000000` nop | `fr.c:1334` mismatch  `bne   $t9, $at, .L70003184` |
| `0x003D74` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x24840004` addiu $a0, $a0, 4 | `0x00000000` nop | `0x00000000` nop | `fr.c:1335` mismatch  `lui   $at, 0x8000` |
| `0x003D78` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x1487FFF5` bne $a0, $a3, 0x3d50 | `0x00000000` nop | `0x00000000` nop | `fr.c:1336` mismatch  `bne   $t7, $at, .L70003184` |
| `0x003D7C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0xA0600003` sb $zero, 3($v1) | `0x00000000` nop | `0x00000000` nop | `fr.c:1337` mismatch  `nop` |
| `0x003D80` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x8FBF0014` lw $ra, 0x14($sp) | `0x00000000` nop | `0x00000000` nop | `fr.c:1338` mismatch  `break 6` |
| `0x003D84` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x27BD0018` addiu $sp, $sp, 0x18 | `0x00000000` nop | `0x00000000` nop | `fr.c:1340` mismatch  `move  $v0, $zero` |
| `0x003D88` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x03E00008` jr $ra | `0x00000000` nop | `0x00000000` nop | `fr.c:1341` mismatch  `bne   $t3, $a1, .L70003198` |
| `0x003D8C` | B_clear_split_8030_8076, B_clear_split_8040_8076, B_clear_split_8060_8076 | `0x00000000` nop | `0x00000000` nop | `0x00000000` nop | `fr.c:1342` mismatch  `sll   $t8, $a1, 0xb` |
| `0x00441C` | F_vi_word | `0x00187840` sll $t7, $t8, 1 | `0x00187880` sll $t7, $t8, 2 | `0x00187840` sll $t7, $t8, 1 | `fr.c:890` match  `sll   $t7, $t8, 1` |
| `0x0046B4` | C_split_select_global | `0x3C038006` lui $v1, 0x8006 | `0x3C048002` lui $a0, 0x8002 | `0x3C048002` lui $a0, 0x8002 | `fr.c:1075` match  `lui   $v1, %hi(g_ViBackIndex)` |
| `0x0046B8` | C_split_select_global | `0x24630879` addiu $v1, $v1, 0x879 | `0x0C00012B` jal 0x4ac | `0x0C00012B` jal 0x4ac | `fr.c:1076` match  `addiu $v1, %lo(g_ViBackIndex) # addiu $v1, $v1, 0x879` |
| `0x0046BC` | C_split_select_global | `0x90780000` lbu $t8, ($v1) | `0x8C84417C` lw $a0, 0x417c($a0) | `0x8C84417C` lw $a0, 0x417c($a0) | `fr.c:1077` match  `lbu   $t8, ($v1)` |
| `0x0046C0` | C_split_select_global | `0x3C0E803B` lui $t6, 0x803b | `0x3C038006` lui $v1, 0x8006 | `0x3C038006` lui $v1, 0x8006 | `fr.c:1078` match  `lui   $t6, %hi(cfb_16) # $t6, 0x803b` |
| `0x0046C4` | C_split_select_global | `0x25CE5000` addiu $t6, $t6, 0x5000 | `0x90780879` lbu $t8, 0x879($v1) | `0x90780879` lbu $t8, 0x879($v1) | `fr.c:1079` match  `addiu $t6, %lo(cfb_16) # addiu $t6, $t6, 0x5000` |
| `0x0046C8` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x00187880` sll $t7, $t8, 2 | `0x3C0F0009` lui $t7, 9 | `0x00187880` sll $t7, $t8, 2 | `fr.c:1080` match  `sll   $t7, $t8, 2` |
| `0x0046CC` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x01F87821` addu $t7, $t7, $t8 | `0x35EF6000` ori $t7, $t7, 0x6000 | `0x01F87821` addu $t7, $t7, $t8 | `fr.c:1081` match  `addu  $t7, $t7, $t8` |
| `0x0046D0` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x000F7880` sll $t7, $t7, 2 | `0x030F0018` mult $t8, $t7 | `0x000F7880` sll $t7, $t7, 2 | `fr.c:1082` match  `sll   $t7, $t7, 2` |
| `0x0046D4` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x01F87823` subu $t7, $t7, $t8 | `0x00000000` nop | `0x01F87823` subu $t7, $t7, $t8 | `fr.c:1083` match  `subu  $t7, $t7, $t8` |
| `0x0046D8` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x000F7880` sll $t7, $t7, 2 | `0x00007812` mflo $t7 | `0x000F7880` sll $t7, $t7, 2 | `fr.c:1084` match  `sll   $t7, $t7, 2` |
| `0x0046DC` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x01F87823` subu $t7, $t7, $t8 | `0x00000000` nop | `0x01F87823` subu $t7, $t7, $t8 | `fr.c:1085` match  `subu  $t7, $t7, $t8` |
| `0x0046E0` | C_split_select_global | `0x3C188002` lui $t8, 0x8002 | `0x3C188002` lui $t8, 0x8002 | `0x3C188002` lui $t8, 0x8002 | `fr.c:1086` match  `lui   $t8, %hi(g_ViBackData)` |
| `0x0046E4` | C_split_select_global | `0x8F1832A8` lw $t8, 0x32a8($t8) | `0x8F1832A8` lw $t8, 0x32a8($t8) | `0x8F1832A8` lw $t8, 0x32a8($t8) | `fr.c:1087` match  `lw    $t8, %lo(g_ViBackData)($t8)` |
| `0x0046E8` | C_fb_calc, C_single_offset_zero, C_split_select_global | `0x000F7AC0` sll $t7, $t7, 0xb | `0x00000000` nop | `0x000F7AC0` sll $t7, $t7, 0xb | `fr.c:1088` match  `sll   $t7, $t7, 0xb` |
| `0x0046EC` | C_split_select_global | `0x01EEC821` addu $t9, $t7, $t6 | `0x01E2C821` addu $t9, $t7, $v0 | `0x01E2C821` addu $t9, $t7, $v0 | `fr.c:1089` match  `addu  $t9, $t7, $t6` |
| `0x0046F0` | C_split_select_global | `0xAF190028` sw $t9, 0x28($t8) | `0xAF190028` sw $t9, 0x28($t8) | `0xAF190028` sw $t9, 0x28($t8) | `fr.c:1090` match  `sw    $t9, 0x28($t8)` |
| `0x006584` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `0x3C02A000` lui $v0, 0xa000 | `0x3C048080` lui $a0, 0x8080 | `0x3C048000` lui $a0, 0x8000 |  |
| `0x006588` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `0x00827025` or $t6, $a0, $v0 | `0x00000000` nop | `0x8C840318` lw $a0, 0x318($a0) |  |
| `0x00658C` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `0x3C018002` lui $at, 0x8002 | `0x3C020009` lui $v0, 9 | `0x3C020002` lui $v0, 2 |  |
| `0x006590` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076, D_mem_fn | `0xAC2E417C` sw $t6, 0x417c($at) | `0x24426000` addiu $v0, $v0, 0x6000 | `0x24425800` addiu $v0, $v0, 0x5800 |  |
| `0x006594` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x3C018002` lui $at, 0x8002 | `0x00822823` subu $a1, $a0, $v0 | `0x00822823` subu $a1, $a0, $v0 |  |
| `0x006598` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x00A27825` or $t7, $a1, $v0 | `0x00A22023` subu $a0, $a1, $v0 | `0x00A22023` subu $a0, $a1, $v0 |  |
| `0x00659C` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x03E00008` jr $ra | `0x3C02A000` lui $v0, 0xa000 | `0x3C02A000` lui $v0, 0xa000 |  |
| `0x0065A0` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0xAC2F4180` sw $t7, 0x4180($at) | `0x00827025` or $t6, $a0, $v0 | `0x00827025` or $t6, $a0, $v0 |  |
| `0x0065A4` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x27BDFFE8` addiu $sp, $sp, -0x18 | `0x3C018002` lui $at, 0x8002 | `0x3C018002` lui $at, 0x8002 |  |
| `0x0065A8` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0xAFBF0014` sw $ra, 0x14($sp) | `0xAC2E417C` sw $t6, 0x417c($at) | `0xAC2E417C` sw $t6, 0x417c($at) |  |
| `0x0065AC` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x3C04803B` lui $a0, 0x803b | `0x00A27825` or $t7, $a1, $v0 | `0x00A27825` or $t7, $a1, $v0 |  |
| `0x0065B0` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x3C05803E` lui $a1, 0x803e | `0x03E00008` jr $ra | `0x03E00008` jr $ra |  |
| `0x0065B4` | D_fb_fixed_8040, D_fb_single_8076A000, D_fb_split_8030_8076, D_fb_split_8040_8076, D_fb_split_8060_8076 | `0x24A5A800` addiu $a1, $a1, -0x5800 | `0xAC2F4180` sw $t7, 0x4180($at) | `0xAC2F4180` sw $t7, 0x4180($at) |  |
| `0x0104DC` | G_mask_word | `0x2401FCFF` addiu $at, $zero, -0x301 | `0x2401FFFF` addiu $at, $zero, -1 | `0x2401FCFF` addiu $at, $zero, -0x301 |  |
| `0x019978` | H_origin_bypass, H_origin_scale, H_origin_width, H_pi_dma | `0x00000000` nop | `0x3C09A440` lui $t1, 0xa440 | `0x00000000` nop |  |
| `0x019980` | H_origin_bypass, H_origin_scale, H_origin_width, H_pi_dma | `0x3C0103FF` lui $at, 0x3ff | `0x10000006` b 0x1999c | `0x3C0103FF` lui $at, 0x3ff |  |
| `0x019984` | H_origin_bypass, H_origin_scale, H_origin_width, H_pi_dma | `0x8E240004` lw $a0, 4($s1) | `0x00000000` nop | `0x8E240004` lw $a0, 4($s1) |  |
| `0x0199B4` | H_origin_width, H_pi_dma, H_width_scale, H_width_vsync | `0x3C18A440` lui $t8, 0xa440 | `0x000C6040` sll $t4, $t4, 1 | `0x3C18A440` lui $t8, 0xa440 |  |
| `0x0199D0` | H_origin_width, H_pi_dma, H_width_scale, H_width_vsync | `0xAF0E0018` sw $t6, 0x18($t8) | `0xADEE0018` sw $t6, 0x18($t7) | `0xAF0E0018` sw $t6, 0x18($t8) |  |
| `0x019A24` | H_origin_scale, H_pi_dma, H_scale, H_width_scale | `0x3C0AA440` lui $t2, 0xa440 | `0x8E2B002C` lw $t3, 0x2c($s1) | `0x3C0AA440` lui $t2, 0xa440 |  |
| `0x019A60` | H_origin_scale, H_pi_dma, H_scale, H_width_scale | `0xAD490030` sw $t1, 0x30($t2) | `0xAD890030` sw $t1, 0x30($t4) | `0xAD490030` sw $t1, 0x30($t2) |  |
| `0x019A64` | H_origin_scale, H_pi_dma, H_scale, H_width_scale | `0x8E2B002C` lw $t3, 0x2c($s1) | `0x000B5842` srl $t3, $t3, 1 | `0x8E2B002C` lw $t3, 0x2c($s1) |  |
| `0x043A48` | J_front_title_480i | `0x2419007E` addiu $t9, $zero, 0x7e | `0x24190097` addiu $t9, $zero, 0x97 | `0x2419007E` addiu $t9, $zero, 0x7e |  |
| `0x043A5C` | J_front_title_480i | `0x247800C3` addiu $t8, $v1, 0xc3 | `0x24780104` addiu $t8, $v1, 0x104 | `0x247800C3` addiu $t8, $v1, 0xc3 |  |
| `0x043A6C` | J_front_title_480i | `0x246600B2` addiu $a2, $v1, 0xb2 | `0x246600F3` addiu $a2, $v1, 0xf3 | `0x246600B2` addiu $a2, $v1, 0xb2 |  |
| `0x043A78` | J_front_title_480i | `0x240700F0` addiu $a3, $zero, 0xf0 | `0x24070109` addiu $a3, $zero, 0x109 | `0x240700F0` addiu $a3, $zero, 0xf0 |  |
| `0x043ABC` | J_front_title_480i | `0x267300B4` addiu $s3, $s3, 0xb4 | `0x267300F5` addiu $s3, $s3, 0xf5 | `0x267300B4` addiu $s3, $s3, 0xb4 |  |
| `0x0460A8` | J_front_title_480i | `0x240B0039` addiu $t3, $zero, 0x39 | `0x8FAC0054` lw $t4, 0x54($sp) | `0x240B0039` addiu $t3, $zero, 0x39 |  |
| `0x0460AC` | J_front_title_480i | `0x240C00F1` addiu $t4, $zero, 0xf1 | `0x8FAB0058` lw $t3, 0x58($sp) | `0x240C00F1` addiu $t4, $zero, 0xf1 |  |
| `0x0460B0` | J_front_title_480i | `0xAFAB0058` sw $t3, 0x58($sp) | `0x258C0005` addiu $t4, $t4, 5 | `0xAFAB0058` sw $t3, 0x58($sp) |  |
| `0x0460C0` | J_front_title_480i | `0x240E00FF` addiu $t6, $zero, 0xff | `0x258E000E` addiu $t6, $t4, 0xe | `0x240E00FF` addiu $t6, $zero, 0xff |  |
| `0x0460D4` | J_front_title_480i | `0x24050037` addiu $a1, $zero, 0x37 | `0x2565FFFE` addiu $a1, $t3, -2 | `0x24050037` addiu $a1, $zero, 0x37 |  |
| `0x0460D8` | J_front_title_480i | `0x240600F0` addiu $a2, $zero, 0xf0 | `0x2586FFFF` addiu $a2, $t4, -1 | `0x240600F0` addiu $a2, $zero, 0xf0 |  |
| `0x0460E0` | J_front_title_480i | `0x24E7003C` addiu $a3, $a3, 0x3c | `0x24E70057` addiu $a3, $a3, 0x57 | `0x24E7003C` addiu $a3, $a3, 0x3c |  |
| `0x046EB8` | J_front_title_480i | `0x3C0143A5` lui $at, 0x43a5 | `0x3C0143F0` lui $at, 0x43f0 | `0x3C0143A5` lui $at, 0x43a5 |  |
| `0x046ED8` | J_front_title_480i | `0x3C0643DC` lui $a2, 0x43dc | `0x3C064420` lui $a2, 0x4420 | `0x3C0643DC` lui $a2, 0x43dc |  |
| `0x046F18` | J_front_height_limit_480i, J_front_title_480i | `0x2418014A` addiu $t8, $zero, 0x14a | `0x241801E0` addiu $t8, $zero, 0x1e0 | `0x2418014A` addiu $t8, $zero, 0x14a |  |
| `0x046F1C` | J_front_title_480i | `0x26AE0023` addiu $t6, $s5, 0x23 | `0x26AE0033` addiu $t6, $s5, 0x33 | `0x26AE0023` addiu $t6, $s5, 0x23 |  |
| `0x046F20` | J_front_title_480i | `0x26AA002A` addiu $t2, $s5, 0x2a | `0x26AA003D` addiu $t2, $s5, 0x3d | `0x26AA002A` addiu $t2, $s5, 0x2a |  |
| `0x04AAAC` | J_front_title_480i | `0x240A0037` addiu $t2, $zero, 0x37 | `0x240A0050` addiu $t2, $zero, 0x50 | `0x240A0037` addiu $t2, $zero, 0x37 |  |
| `0x04AAB0` | J_front_title_480i | `0x240B00A7` addiu $t3, $zero, 0xa7 | `0x240B00F3` addiu $t3, $zero, 0xf3 | `0x240B00A7` addiu $t3, $zero, 0xa7 |  |
| `0x04AAC4` | J_front_title_480i | `0x24040140` addiu $a0, $zero, 0x140 | `0x240401D1` addiu $a0, $zero, 0x1d1 | `0x24040140` addiu $a0, $zero, 0x140 |  |
| `0x04D42C` | J_front_resolution_480i, J_front_title_480i | `0x240501B8` addiu $a1, $zero, 0x1b8 | `0x24050280` addiu $a1, $zero, 0x280 | `0x240501B8` addiu $a1, $zero, 0x1b8 | `front.c:8959` match  `li    $a1, 440` |
| `0x04D434` | J_front_resolution_480i, J_front_title_480i | `0x2406014A` addiu $a2, $zero, 0x14a | `0x240601E0` addiu $a2, $zero, 0x1e0 | `0x2406014A` addiu $a2, $zero, 0x14a | `front.c:8961` match  `li    $a2, 330` |
| `0x04DAE0` | J_front_resolution_480i, J_front_title_480i | `0x240401B8` addiu $a0, $zero, 0x1b8 | `0x24040280` addiu $a0, $zero, 0x280 | `0x240401B8` addiu $a0, $zero, 0x1b8 |  |
| `0x04DAE8` | J_front_resolution_480i, J_front_title_480i | `0x2405014A` addiu $a1, $zero, 0x14a | `0x240501E0` addiu $a1, $zero, 0x1e0 | `0x2405014A` addiu $a1, $zero, 0x14a |  |
| `0x04DAEC` | J_front_resolution_480i, J_front_title_480i | `0x240401B8` addiu $a0, $zero, 0x1b8 | `0x24040280` addiu $a0, $zero, 0x280 | `0x240401B8` addiu $a0, $zero, 0x1b8 |  |
| `0x04DAF4` | J_front_resolution_480i, J_front_title_480i | `0x2405014A` addiu $a1, $zero, 0x14a | `0x240501E0` addiu $a1, $zero, 0x1e0 | `0x2405014A` addiu $a1, $zero, 0x14a |  |
| `0x04F354` | E_direct_dim0, E_direct_dims | `0x8C42A8C4` lw $v0, -0x573c($v0) | `0x028001E0`  | `0x014000F0` tge $t2, $zero, 3 |  |
| `0x04F35C` | E_direct_dim1, E_direct_dim1_height480, E_direct_dim1_width640, E_direct_dims | `0x00000000` nop | `0x028001E0`  | `0x01B8014A`  |  |
| `0x050148` | J_front_title_480i | `0x25190011` addiu $t9, $t0, 0x11 | `0x2519001D` addiu $t9, $t0, 0x1d | `0x25190011` addiu $t9, $t0, 0x11 | `unk_01B240.c:299` match  `addiu $t9, $t0, 0x11` |
| `0x050168` | J_front_title_480i | `0x25190010` addiu $t9, $t0, 0x10 | `0x2519001C` addiu $t9, $t0, 0x1c | `0x25190010` addiu $t9, $t0, 0x10 | `unk_01B240.c:307` match  `addiu $t9, $t0, 0x10` |
| `0x0501AC` | J_front_title_480i | `0x2921012C` slti $at, $t1, 0x12c | `0x292101AE` slti $at, $t1, 0x1ae | `0x2921012C` slti $at, $t1, 0x12c | `unk_01B240.c:325` match  `slti  $at, $t1, 0x12c` |
| `0x0501B4` | J_front_title_480i | `0x261001B8` addiu $s0, $s0, 0x1b8 | `0x26100280` addiu $s0, $s0, 0x280 | `0x261001B8` addiu $s0, $s0, 0x1b8 | `unk_01B240.c:327` match  `addiu $s0, $s0, 0x1b8` |
| `0x0BB730` | I_gameplay_viewport_480i | `0x24020140` addiu $v0, $zero, 0x140 | `0x24020280` addiu $v0, $zero, 0x280 | `0x24020140` addiu $v0, $zero, 0x140 | `bondview.c:15226` mismatch  `addu  $at, $at, $t1` |
| `0x0BB740` | I_gameplay_viewport_480i | `0x240201B8` addiu $v0, $zero, 0x1b8 | `0x24020280` addiu $v0, $zero, 0x280 | `0x240201B8` addiu $v0, $zero, 0x1b8 | `bondview.c:15231` mismatch  `b     .L7F088DE4` |
| `0x0BB754` | I_gameplay_viewport_480i | `0x240200F0` addiu $v0, $zero, 0xf0 | `0x240201E0` addiu $v0, $zero, 0x1e0 | `0x240200F0` addiu $v0, $zero, 0xf0 | `bondview.c:15237` mismatch  `bne   $v0, $t2, .L7F088D90` |
| `0x0BB764` | I_gameplay_viewport_480i | `0x2402014A` addiu $v0, $zero, 0x14a | `0x240201E0` addiu $v0, $zero, 0x1e0 | `0x2402014A` addiu $v0, $zero, 0x14a | `bondview.c:15241` mismatch  `nop` |
| `0x0BB790` | I_gameplay_viewport_480i | `0x2402009F` addiu $v0, $zero, 0x9f | `0x2402013F` addiu $v0, $zero, 0x13f | `0x2402009F` addiu $v0, $zero, 0x9f | `bondview.c:15255` mismatch  `lw    $t3, 0xc($s0)` |
| `0x0BB7A4` | I_gameplay_viewport_480i | `0x240201B8` addiu $v0, $zero, 0x1b8 | `0x24020280` addiu $v0, $zero, 0x280 | `0x240201B8` addiu $v0, $zero, 0x1b8 | `bondview.c:15260` mismatch  `lw    $a1, 8($s0)` |
| `0x0BB7C0` | I_gameplay_viewport_480i | `0x24020140` addiu $v0, $zero, 0x140 | `0x24020280` addiu $v0, $zero, 0x280 | `0x24020140` addiu $v0, $zero, 0x140 | `bondview.c:15271` mismatch  `b     .L7F088DE4` |
| `0x0BB7D4` | I_gameplay_viewport_480i | `0x24020140` addiu $v0, $zero, 0x140 | `0x24020280` addiu $v0, $zero, 0x280 | `0x24020140` addiu $v0, $zero, 0x140 | `bondview.c:15280` mismatch  `lw    $v0, ($s0)` |
| `0x0BB7DC` | I_gameplay_viewport_480i | `0x24020140` addiu $v0, $zero, 0x140 | `0x24020280` addiu $v0, $zero, 0x280 | `0x24020140` addiu $v0, $zero, 0x140 | `bondview.c:15282` mismatch  `bnel  $v0, $at, .L7F088D34` |
| `0x0BB7E0` | I_gameplay_viewport_480i | `0x24020140` addiu $v0, $zero, 0x140 | `0x24020280` addiu $v0, $zero, 0x280 | `0x24020140` addiu $v0, $zero, 0x140 | `bondview.c:15283` mismatch  `sltiu $at, $v0, 7` |
| `0x0BB83C` | I_gameplay_viewport_480i | `0x240200A1` addiu $v0, $zero, 0xa1 | `0x24020141` addiu $v0, $zero, 0x141 | `0x240200A1` addiu $v0, $zero, 0xa1 |  |
| `0x0BB874` | I_gameplay_viewport_480i | `0x2402006D` addiu $v0, $zero, 0x6d | `0x240200E5` addiu $v0, $zero, 0xe5 | `0x2402006D` addiu $v0, $zero, 0x6d |  |
| `0x0BB89C` | I_gameplay_viewport_480i | `0x240200F8` addiu $v0, $zero, 0xf8 | `0x240201F0` addiu $v0, $zero, 0x1f0 | `0x240200F8` addiu $v0, $zero, 0xf8 |  |
| `0x0BB8B8` | I_gameplay_viewport_480i | `0x240200BE` addiu $v0, $zero, 0xbe | `0x2402017C` addiu $v0, $zero, 0x17c | `0x240200BE` addiu $v0, $zero, 0xbe |  |
| `0x0BB8C0` | I_gameplay_viewport_480i | `0x24020130` addiu $v0, $zero, 0x130 | `0x24020260` addiu $v0, $zero, 0x260 | `0x24020130` addiu $v0, $zero, 0x130 |  |
| `0x0BB8FC` | I_gameplay_viewport_480i | `0x244200B4` addiu $v0, $v0, 0xb4 | `0x24420168` addiu $v0, $v0, 0x168 | `0x244200B4` addiu $v0, $v0, 0xb4 |  |
| `0x0BB91C` | I_gameplay_viewport_480i | `0x240200DC` addiu $v0, $zero, 0xdc | `0x240201B8` addiu $v0, $zero, 0x1b8 | `0x240200DC` addiu $v0, $zero, 0xdc |  |
| `0x0BB944` | I_gameplay_viewport_480i | `0x24420088` addiu $v0, $v0, 0x88 | `0x24420110` addiu $v0, $v0, 0x110 | `0x24420088` addiu $v0, $v0, 0x88 |  |
| `0x0BB954` | I_gameplay_viewport_480i | `0x240200DC` addiu $v0, $zero, 0xdc | `0x240201B8` addiu $v0, $zero, 0x1b8 | `0x240200DC` addiu $v0, $zero, 0xdc |  |
| `0x0BB9A0` | I_gameplay_viewport_480i | `0x24020079` addiu $v0, $zero, 0x79 | `0x240200F1` addiu $v0, $zero, 0xf1 | `0x24020079` addiu $v0, $zero, 0x79 |  |
| `0x0BB9D8` | I_gameplay_viewport_480i | `0x24020079` addiu $v0, $zero, 0x79 | `0x240200F1` addiu $v0, $zero, 0xf1 | `0x24020079` addiu $v0, $zero, 0x79 |  |
| `0x0BBA60` | I_gameplay_viewport_480i | `0x2442001E` addiu $v0, $v0, 0x1e | `0x2442003C` addiu $v0, $v0, 0x3c | `0x2442001E` addiu $v0, $v0, 0x1e |  |
| `0x0BBA80` | I_gameplay_viewport_480i | `0x2402000A` addiu $v0, $zero, 0xa | `0x24020014` addiu $v0, $zero, 0x14 | `0x2402000A` addiu $v0, $zero, 0xa |  |
| `0x0BBAA8` | I_gameplay_viewport_480i | `0x24420034` addiu $v0, $v0, 0x34 | `0x24420068` addiu $v0, $v0, 0x68 | `0x24420034` addiu $v0, $v0, 0x34 |  |
| `0x106ED4` | J_expanded_menu_resolution_480i, J_front_title_480i | `0x240F01B8` addiu $t7, $zero, 0x1b8 | `0x240F0280` addiu $t7, $zero, 0x280 | `0x240F01B8` addiu $t7, $zero, 0x1b8 |  |
| `0x106EE4` | J_expanded_menu_resolution_480i, J_front_title_480i | `0x2418014A` addiu $t8, $zero, 0x14a | `0x241801E0` addiu $t8, $zero, 0x1e0 | `0x2418014A` addiu $t8, $zero, 0x14a |  |
| `0x106EF0` | J_expanded_menu_resolution_480i, J_front_title_480i | `0x24190140` addiu $t9, $zero, 0x140 | `0x24190280` addiu $t9, $zero, 0x280 | `0x24190140` addiu $t9, $zero, 0x140 |  |
| `0x106F10` | J_expanded_menu_resolution_480i, J_front_title_480i | `0x240800F0` addiu $t0, $zero, 0xf0 | `0x240801E0` addiu $t0, $zero, 0x1e0 | `0x240800F0` addiu $t0, $zero, 0xf0 |  |
| `0x106F24` | J_expanded_menu_resolution_480i, J_front_title_480i | `0x24090078` addiu $t1, $zero, 0x78 | `0x240901E0` addiu $t1, $zero, 0x1e0 | `0x24090078` addiu $t1, $zero, 0x78 |  |
