/** Where "出陣する" goes. Set PUBLIC_GAME_URL at build time to the deployed game. */
export const GAME_URL: string = import.meta.env.PUBLIC_GAME_URL ?? 'https://github.com/kyokot/bokosuka_war_awaken';

/** figurines are drawn from lower down than buildings, so their faces stay readable */
export const FIG = { squash: 0.45, gap: 1.25 } as const;
