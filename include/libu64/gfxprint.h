#ifndef GFXPRINT_H
#define GFXPRINT_H

#include "types.h"
#include "libu64/u64types.h"
#include "PR/mbi.h"
// #include "va_args.h"

#ifdef __cplusplus
extern "C"{
#endif

#define GFXPRINT_NUM_SUBPIXELS 4
#define GFXPRINT_PIXELS_PER_BLOCK 8
#define GFXPRINT_PAD GFXPRINT_PIXELS_PER_BLOCK * GFXPRINT_NUM_SUBPIXELS

#define GFXPRINT_FLAG_KANA_MODE (1 << 0) /* Japanese characters displayed as hiragana or katakana */
#define GFXPRINT_FLAG_GRADIENT (1 << 1) /* Gradient state */
#define GFXPRINT_FLAG_SHADOW (1 << 2) /* Shadow state */
#define GFXPRINT_FLAG_CHANGED (1 << 3) /* Text changed */
/* Unused...? */
#define GFXPRINT_FLAG_HIGHRES (1 << 6) /* Highres text */
#define GFXPRINT_FLAG_OPENED (1 << 7) /* Open state */

#define GFXPRINT_KANA_MODE_KATAKANA 0
#define GFXPRINT_KANA_MODE_HIRAGANA 1

#define GFXPRINT_CLEAR_GRADIENT_CHAR "\x8A"
#define GFXPRINT_ENABLE_GRADIENT_CHAR "\x8B"

#define GFXPRINT_KATAKANA_MODE_CHAR "\x8C"
#define GFXPRINT_HIRAGANA_MODE_CHAR "\x8D"

#define GFXPRINT_UNUSED_CHAR "\x8E"

/* NOTE: this should be a void return type but we're going to use a void* for readibility */
typedef void* (*PrintCallback)(void*, const char*, int);
typedef struct gfxprint_obj  {
    PrintCallback prout_func; /* Current print out func */
    Gfx* glistp; /* Current display list to write text to */
    u16 position_x; /* Display coords (sub-pixel units) */
    u16 position_y; /* Display coords (sub-pixel units) */
    u16 offset_x; /* Display offset */
    u8 offset_y; /* Display offset */
    u8 flags; /* 1: Kana mode -> 0: Katakana/1: Hiragana
                 2: Gradient displayed
                 4: Shadow displayed
                 8: Attribute changed
                 64: Low-res -> high-res conversion
                 128: Opened state */
    rgba8888 color; /* Current font color */
    u8 dummy[28]; /* For size compatibility */
} gfxprint_t;

/* Default gfxprint flag values set in game_ct func, default value is 0x40 (GFXPRINT_FLAG_HIGHRES on) */
extern u8 __gfxprint_default_flags;

extern u16 gfxprint_moji_tlut[];
extern u8 gfxprint_font[];

/* Macros for quickly checking state of gfxprint struct */
#define gfxprint_isFlagOn(gfxprint, flag) ((gfxprint->flags & flag) != 0)
#define gfxprint_setFlag(gfxprint, flag) (gfxprint->flags |= flag)
#define gfxprint_clrFlag(gfxprint, flag) (gfxprint->flags &= ~flag)

#define gfxprint_isOpened(gfxprint) (gfxprint_isFlagOn(gfxprint, GFXPRINT_FLAG_OPENED))
#define gfxprint_setOpened(gfxprint) (gfxprint_setFlag(gfxprint, GFXPRINT_FLAG_OPENED))
#define gfxprint_clrOpened(gfxprint) (gfxprint_clrFlag(gfxprint, GFXPRINT_FLAG_OPENED))

#define gfxprint_isHighres(gfxprint) (gfxprint_isFlagOn(gfxprint, GFXPRINT_FLAG_HIGHRES))
#define gfxprint_setHighres(gfxprint) (gfxprint_setFlag(gfxprint, GFXPRINT_FLAG_HIGHRES))
#define gfxprint_clrHighres(gfxprint) (gfxprint_clrFlag(gfxprint, GFXPRINT_FLAG_HIGHRES))

#define gfxprint_isHiragana(gfxprint) ((gfxprint->flags & GFXPRINT_FLAG_KANA_MODE) != GFXPRINT_KANA_MODE_KATAKANA)
#define gfxprint_isKatakana(gfxprint) ((gfxprint->flags & GFXPRINT_FLAG_KANA_MODE) == GFXPRINT_KANA_MODE_KATAKANA)
#define gfxprint_setHiragana(gfxprint) (gfxprint->flags |= GFXPRINT_FLAG_KANA_MODE)
#define gfxprint_setKatakana(gfxprint) (gfxprint->flags &= ~GFXPRINT_FLAG_KANA_MODE)

#define gfxprint_isGradient(gfxprint) (gfxprint_isFlagOn(gfxprint, GFXPRINT_FLAG_GRADIENT))
#define gfxprint_setGradient(gfxprint) (gfxprint_setFlag(gfxprint, GFXPRINT_FLAG_GRADIENT))
#define gfxprint_clrGradient(gfxprint) (gfxprint_clrFlag(gfxprint, GFXPRINT_FLAG_GRADIENT))

#define gfxprint_isShadow(gfxprint) (gfxprint_isFlagOn(gfxprint, GFXPRINT_FLAG_SHADOW))
#define gfxprint_setShadow(gfxprint) (gfxprint_setFlag(gfxprint, GFXPRINT_FLAG_SHADOW))
#define gfxprint_clrShadow(gfxprint) (gfxprint_clrFlag(gfxprint, GFXPRINT_FLAG_SHADOW))

#define gfxprint_isChanged(gfxprint) (gfxprint_isFlagOn(gfxprint, GFXPRINT_FLAG_CHANGED))
#define gfxprint_setChanged(gfxprint) (gfxprint_setFlag(gfxprint, GFXPRINT_FLAG_CHANGED))
#define gfxprint_clrChanged(gfxprint) (gfxprint_clrFlag(gfxprint, GFXPRINT_FLAG_CHANGED))

static void gfxprint_setup(gfxprint_t* gfxprint);
static void gfxprint_putc1(gfxprint_t* gfxprint, char c);
static void* gfxprint_prout(void* gfxprint, const char* buffer, int n);

extern void gfxprint_color(gfxprint_t* gfxprint, u32 r, u32 g, u32 b, u32 a);

extern void gfxprint_locate(gfxprint_t* gfxprint, int x, int y);
extern void gfxprint_locate8x8(gfxprint_t* gfxprint, int x, int y);
extern void gfxprint_setoffset(gfxprint_t* gfxprint, int x, int y);

extern void gfxprint_putc(gfxprint_t* gfxprint, char c);
extern void gfxprint_write(gfxprint_t* gfxprint, const void* buffer, size_t size, size_t n);
extern void gfxprint_puts(gfxprint_t* gfxprint, char* string);

extern void gfxprint_init(gfxprint_t* gfxprint);
extern void gfxprint_cleanup(gfxprint_t* gfxprint);

extern void gfxprint_open(gfxprint_t* gfxprint, Gfx* glistp);
extern Gfx* gfxprint_close(gfxprint_t* gfxprint);

extern int gfxprint_vprintf(gfxprint_t* gfxprint, const char* fmt, va_list ap);
extern int gfxprint_printf(gfxprint_t* gfxprint, const char* fmt, ...);

/* Custom macro to match gDPLoadTLUT_pal16 but with N palette entries */
#define gDPLoadTLUT_palX(pkt, pal, dram, count)				\
do {									\
	gDPSetTextureImage(pkt, G_IM_FMT_RGBA, G_IM_SIZ_16b, 1, dram);	\
	gDPTileSync(pkt);						\
	gDPSetTile(pkt, 0, 0, 0, (256+(((pal)&0xf)*16)),		\
		G_TX_LOADTILE, 0 , 0, 0, 0, 0, 0, 0);			\
	gDPLoadSync(pkt);						\
	gDPLoadTLUTCmd(pkt, G_TX_LOADTILE, (count)-1);				\
	gDPPipeSync(pkt);						\
} while (0)

#ifdef __cplusplus
}
#endif
#endif
