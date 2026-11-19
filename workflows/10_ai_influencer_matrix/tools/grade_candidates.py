"""调色候选（2026-11-19）。B2 = 当前默认；B3~B6 针对脸上油光。"""
GRAIN = "gblur=sigma=0.5,noise=c0s=8:c0f=t+u:c1s=3:c1f=t+u:c2s=3:c2f=t+u,vignette=angle=PI/6.5"
SPLIT = "colorbalance=rs=-0.04:bs=0.05:rm=0.03:gm=0.01:bm=-0.02:rh=0.04:gh=0.015:bh=-0.03"
HALO = "split[g1][g2];[g2]curves=master='0/0 0.6/0 1/0.8',gblur=sigma=28[gh];[g1][gh]blend=all_mode=screen:all_opacity={op},"
# 去油光：只在亮部（反光）起作用——亮部压暗一点、去掉高光里的锐利纹理，再按亮度遮罩柔和地合回去
DESHINE = ("format=gbrp,split=3[o][d][m];"
           "[d]curves=master='0/0 0.55/0.55 0.75/{k} 1/{top}',gblur=sigma=2.5[dd];"
           "[m]format=gray,curves=master='0/0 {lo}/0 {hi}/1 1/1',gblur=sigma=8,format=gbrp[mm];"
           "[o][dd][mm]maskedmerge,format=yuv420p,")
GRADES = {
    "B2": "eq=saturation=0.92:contrast=1.05:gamma=1.08,curves=master='0/0.02 0.25/0.27 0.5/0.57 0.75/0.82 1/0.97',"
          + SPLIT + "," + HALO.format(op=0.35) + GRAIN,
    # B3：不加高光柔光，高光软压（肩部滚降）
    "B3": "eq=saturation=0.92:contrast=1.0:gamma=1.08,curves=master='0/0.02 0.25/0.27 0.5/0.56 0.75/0.78 0.9/0.86 1/0.9',"
          + SPLIT + "," + GRAIN,
    # B4：B3 + 局部去油光
    "B4": DESHINE.format(k="0.70", top="0.80", lo="0.62", hi="0.85")
          + "eq=saturation=0.92:contrast=1.0:gamma=1.08,curves=master='0/0.02 0.25/0.27 0.5/0.56 0.75/0.78 0.9/0.86 1/0.9',"
          + SPLIT + "," + GRAIN,
    # B5：B4 去油光更狠 + 哑光胶片（黑位抬起、对比更低、偏暖）
    "B5": DESHINE.format(k="0.66", top="0.74", lo="0.55", hi="0.80")
          + "eq=saturation=0.88:contrast=0.96:gamma=1.06,curves=master='0/0.05 0.25/0.29 0.5/0.55 0.75/0.76 1/0.88',"
          + "colorbalance=rs=-0.03:bs=0.04:rm=0.04:gm=0.015:bm=-0.03:rh=0.03:bh=-0.02," + GRAIN,
    # B6：B4 + 再亮一点 + 很轻的高光柔光（只要氛围，不碰脸）
    "B6": DESHINE.format(k="0.70", top="0.80", lo="0.62", hi="0.85")
          + "eq=saturation=0.92:contrast=1.02:gamma=1.13,curves=master='0/0.02 0.25/0.28 0.5/0.58 0.75/0.79 0.9/0.87 1/0.91',"
          + SPLIT + "," + HALO.format(op=0.12) + GRAIN,
}
