import { theme, type ThemeConfig } from 'antd';

/**
 * AntD theme config aligned with Obsidian Spatial.
 * Pure-black surfaces, white primary, zero radius, Geist typography.
 */
export const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#ffffff',
    colorInfo: '#ffffff',
    colorSuccess: '#6bfe9c',
    colorWarning: '#fbbf24',
    colorError: '#ffb4ab',

    colorBgBase: '#000000',
    colorBgContainer: '#0a0a0a',
    colorBgElevated: '#121212',
    colorBgLayout: '#000000',

    colorText: '#e3e2e2',
    colorTextSecondary: '#c4c7c8',
    colorTextTertiary: '#8e9192',
    colorTextDescription: '#8e9192',

    colorBorder: '#1a1a1a',
    colorBorderSecondary: '#333333',

    // Zero-radius geometry — engineered aesthetic
    borderRadius: 0,
    borderRadiusLG: 0,
    borderRadiusSM: 0,

    fontFamily:
      'var(--font-geist-sans), Geist, Inter, system-ui, -apple-system, sans-serif',
    fontFamilyCode:
      'var(--font-jetbrains), "JetBrains Mono", Consolas, monospace',
    controlHeight: 38,
    wireframe: true,
  },
  components: {
    Button: {
      controlHeight: 40,
      fontWeight: 500,
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
      // primary 按钮背景色为 #ffffff，darkAlgorithm 推导出的文字色偏浅，
      // 显式指定为深色，保证白底深字对比清晰。
      primaryColor: '#0a0a0a',
      defaultBg: '#0a0a0a',
      defaultColor: '#e3e2e2',
      defaultBorderColor: '#444748',
      defaultHoverColor: '#ffffff',
      defaultHoverBg: '#1f2020',
      defaultHoverBorderColor: '#8e9192',
      defaultActiveColor: '#ffffff',
      defaultActiveBg: '#1b1c1c',
    },
    Input: {
      colorBgContainer: '#0a0a0a',
      activeShadow: 'none',
    },
    Card: {
      colorBgContainer: '#0a0a0a',
      boxShadowTertiary: 'none',
    },
    Modal: {
      contentBg: '#121212',
      headerBg: '#121212',
    },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
    },
    Drawer: {
      colorBgElevated: '#0a0a0a',
    },
  },
};

/**
 * Channel accent mapping.
 * Under Obsidian Spatial the palette is strictly monochromatic; the green
 * tertiary is reserved for functional indicators. Channel identity is now
 * expressed via 1px stroke and label-mono text rather than hue.
 */
export const channelThemes: Record<string, string> = {
  channel: '#ffffff',
  policy: '#6bfe9c',
};
