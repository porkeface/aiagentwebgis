/**
 * Day-route color palette — built from a base set of 16 hues, then filtered
 * to drop any colour whose hue is too close to a category colour.  The base
 * set is hand-picked to live in the warm/cool gaps the category palette
 * doesn't touch, so we keep most of the 16 even after filtering.
 */
const DAY_COLOR_PALETTE: string[] = [
  '#f43f5e',  // rose       (warm red-pink)
  '#0ea5e9',  // sky        (cyan-blue)
  '#84cc16',  // lime       (yellow-green)
  '#f59e0b',  // amber      (yellow-orange)
  '#a855f7',  // purple
  '#14b8a6',  // teal       (cyan-green)
  '#ec4899',  // pink       (magenta)
  '#facc15',  // yellow
  '#6366f1',  // indigo     (blue-violet)
  '#22c55e',  // green
  '#fb923c',  // orange
  '#06b6d4',  // cyan
  '#d946ef',  // fuchsia
  '#fb7185',  // coral
  '#a3a3a3',  // neutral grey (fallback)
  '#dc2626',  // brick red
]

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ]
}

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  const l = (max + min) / 2
  let h = 0, s = 0
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)); break
      case g: h = ((b - r) / d + 2); break
      case b: h = ((r - g) / d + 4); break
    }
    h /= 6
  }
  return [h, s, l]
}

/** Reject palette colours whose hue is within 15° of a category hue.
 *  Threshold is tight — only ever blocks near-identical hues, so most of
 *  the 16-colour base palette survives even with the 5 POI hues filling
 *  large swaths of the colour wheel. */
function isTooClose(hexA: string, rgbB: [number, number, number]): boolean {
  const [ar, ag, ab] = hexToRgb(hexA)
  const [ha] = rgbToHsl(ar, ag, ab)
  const [hb] = rgbToHsl(rgbB[0], rgbB[1], rgbB[2])
  if (ha === 0 || hb === 0) return false
  const diff = Math.min(Math.abs(ha - hb), 1 - Math.abs(ha - hb)) * 360
  return diff < 15
}

/** The day-colour palette (category colours excluded). Lazily initialised
 *  after POI_GROUPS is defined below — see end of file. */
export let DAY_COLORS: readonly string[] = []

// ── 5 大类 POI ─────────────────────────────────────────────────────────────

// SVG icons — kept inline so they're guaranteed to render identically on
// every browser. Bed (🏨 accommodation) and camera (📷 landmarks) used to
// be emoji, but emoji rendering varies wildly across Windows / macOS /
// Android. SVG eliminates that variance.

const POI_ICONS = {
  sightseeing:
    '<svg viewBox="0 0 24 24" width="10" height="10" fill="white">' +
    '<path d="M12 2L4 6v6c0 5 3.5 9.5 8 10 4.5-.5 8-5 8-10V6l-8-4zm0 4.5l5 2.5v3c0 3.5-2.5 7-5 7.7-2.5-.7-5-4.2-5-7.7v-3l5-2.5z"/>' +
    "</svg>",
  food:
    '<svg viewBox="0 0 24 24" width="10" height="10" fill="white">' +
    '<path d="M11 9H9V2H7v7H5V2H3v7c0 2.1 1.7 3.8 3.8 3.9L8 21h2l1.2-8.1C12.7 12.8 14 11.1 14 9V2h-2v7h-1V2zm7-7v9c0 2.5-2 4.5-4.5 4.5V21h-2v-8.5C13 12.5 15 10.5 15 8V2h3z"/>' +
    "</svg>",
  drinks:
    '<svg viewBox="0 0 24 24" width="10" height="10" fill="white">' +
    '<path d="M20 3H4v10c0 2.2 1.8 4 4 4h8c2.2 0 4-1.8 4-4V5c0-1.1-.9-2-2-2zm0 12H4V5h16v10zm-2 5H6v-2h12v2z"/>' +
    "</svg>",
  shopping:
    '<svg viewBox="0 0 24 24" width="10" height="10" fill="white">' +
    '<path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.6-1.4 2.5c-.2.4-.2.9.1 1.2.3.4.7.7 1.2.7h12v-2H7.4c-.1 0-.2-.1-.2-.2v-.1L8.1 13h7.4c.7 0 1.4-.4 1.7-1l3.6-6.5c.1-.2.2-.4.2-.6 0-.6-.4-1-1-1H5.2L4.3 1H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/>' +
    "</svg>",
  accommodation:
    '<svg viewBox="0 0 24 24" width="12" height="12" fill="white">' +
    '<path d="M20 10V7c0-1.1-.9-2-2-2h-3V3H9v2H6c-1.1 0-2 .9-2 2v3c-1.7 0-3 1.3-3 3v6h2v-3h18v3h2v-6c0-1.7-1.3-3-3-3zM6 7h12v3H6V7zm-3 9c0-.5.5-1 1-1h16c.5 0 1 .5 1 1v1H3v-1z"/>' +
    "</svg>",
}

export function categorySvg(group: POIGroup): string {
  return POI_ICONS[group] ?? ""
}

export const POI_GROUPS = {
  /** 景点：风景名胜、博物馆、公园、寺庙、历史遗址、游乐等 */
  sightseeing: {
    icon: POI_ICONS.sightseeing,
    label: "景点",
    color: "#0891b2",
    keywords: [
      "风景名胜", "国家级景点", "世界遗产", "博物馆", "展览馆", "美术馆",
      "科技馆", "寺庙道观", "教堂", "纪念馆", "公园", "城市广场",
      "动物园", "植物园", "水族馆", "游乐园", "主题公园", "国家级森林公园",
      "海滩", "岛屿", "温泉", "文化街区", "历史遗址", "古村镇", "特色街区",
      "创意园区", "观景台", "缆车", "登山", "徒步路线", "自然风光",
      "特色村落", "宗教场所", "历史文化街区", "会展中心", "夜游", "游船",
      "运动场馆", "滑雪场", "高尔夫球场", "电影院", "剧院", "音乐厅",
      "度假区", "度假村", "山庄", "公园广场", "红色景区", "旅游景点",
      "风景名胜相关", "红色旅游", "体育休闲服务", "体育休闲服务场所",
      "疗养院", "休闲场所",
    ],
  },
  /** 美食：餐厅、小吃、夜市、美食街 */
  food: {
    icon: POI_ICONS.food,
    label: "美食",
    color: "#e11d48",
    keywords: [
      "餐饮服务", "中餐厅", "外国餐厅", "特色餐厅", "美食街", "夜市", "小吃",
      "火锅", "海鲜", "日料", "韩料", "西餐", "农家菜", "面包甜点",
      "冷饮店", "咖啡厅", "茶社", "茶馆", "茶艺馆", "奶茶店",
      "冰淇淋", "甜品", "糕点", "烧烤", "大排档", "用餐",
      "清真", "素食", "自助餐", "家常菜", "私房菜",
      "糕饼店", "福建菜", "快餐厅", "餐馆", "茶餐厅",
    ],
  },
  /** 饮品：咖啡、茶、酒吧、奶茶 */
  drinks: {
    icon: POI_ICONS.drinks,
    label: "饮品",
    color: "#475569",
    keywords: [
      "咖啡厅", "咖啡", "咖啡馆", "茶馆", "茶社", "茶艺馆", "茶室",
      "酒吧", "酒馆", "清吧", "精酿", "奶茶店", "奶茶",
      "冷饮店", "冷饮", "水吧", "果汁",
    ],
  },
  /** 购物：商场、步行街、市场、免税 */
  shopping: {
    icon: POI_ICONS.shopping,
    label: "购物",
    color: "#059669",
    keywords: [
      "购物服务", "购物中心", "商业步行街", "百货商场", "百货", "超市",
      "市场", "免税店", "奥莱", "奥特莱斯", "文创店", "纪念品",
      "便利店", "专卖店", "品牌店", "家居建材", "家电卖场",
      "电子城", "数码", "花鸟鱼虫", "古玩", "旧货", "商场", "普通商场",
    ],
  },
  /** 住宿：酒店、民宿、青旅 */
  accommodation: {
    icon: POI_ICONS.accommodation,
    label: "住宿",
    color: "#7c3aed",
    keywords: [
      "住宿服务", "酒店", "宾馆", "四星级宾馆", "五星级宾馆", "民宿",
      "青旅", "青年旅舍", "客栈", "度假村", "招待所", "旅馆",
      "经济型酒店", "星级酒店", "公寓式酒店", "别墅", "露营地",
      "宾馆酒店",
    ],
  },
} as const

type POIGroup = keyof typeof POI_GROUPS

/** Resolve any Amap category string to the closest POI group key.
 *
 * Amap 返回多层分类，如 "住宿服务;宾馆酒店;四星级宾馆" 或
 * "购物服务;商场;购物中心"。检查全部分层（不只取第一个），并优先
 * 匹配最具体的中间层（"商场"、"宾馆酒店"等）。
 */
export function classifyPOI(cat: string | undefined): POIGroup {
  if (!cat) return "sightseeing"

  // 拆分多级 category，并按从细到粗的顺序扫描每一层
  const segments = cat.split(";")
  for (const group of Object.keys(POI_GROUPS) as POIGroup[]) {
    for (const segment of segments) {
      for (const kw of POI_GROUPS[group].keywords) {
        if (segment.includes(kw)) return group
      }
    }
  }
  return "sightseeing"
}

/** SVG icon for a POI category. */
export function categoryIcon(cat: string | undefined): string {
  return POI_GROUPS[classifyPOI(cat)].icon
}

/** Brand colour for a POI category — used for the circular marker background. */
export function categoryColor(cat: string | undefined): string {
  return POI_GROUPS[classifyPOI(cat)].color
}

// Initialise the day palette now that POI_GROUPS is fully defined.
{
  const POI_RGB = Object.values(POI_GROUPS).map((g) => g.color).map(hexToRgb)
  DAY_COLORS = DAY_COLOR_PALETTE.filter((c) => !POI_RGB.some((p) => isTooClose(c, p)))
}
