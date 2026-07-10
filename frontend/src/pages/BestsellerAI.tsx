import { useState } from "react";
import {
  MessagesSquare,
  User,
  Users,
  Briefcase,
  LayoutDashboard,
  BarChart3,
  CalendarClock,
  SlidersHorizontal,
  Settings,
  ChevronsLeft,
  ChevronDown,
  Search,
  Lightbulb,
  TrendingUp,
  MoreVertical,
  Check,
  Filter,
  Calendar,
  LineChart,
  BarChart2,
  ExternalLink
} from "lucide-react";
import "./BestsellerAI.css";

type NavKey =
  | "all"
  | "profile"
  | "team"
  | "deals"
  | "dashboard"
  | "reports"
  | "meeting"
  | "personalization"
  | "settings"
  | "collapse";

type IconType = typeof User;

const NAV_MAIN: { key: NavKey; label: string; icon: IconType }[] = [
  { key: "all", label: "Все коммуникации", icon: MessagesSquare },
  { key: "profile", label: "Профайл", icon: User },
  { key: "team", label: "Команда", icon: Users },
  { key: "deals", label: "Сделки", icon: Briefcase },
  { key: "dashboard", label: "Дашборд", icon: LayoutDashboard },
  { key: "reports", label: "Отчеты", icon: BarChart3 },
  { key: "meeting", label: "Режим встречи", icon: CalendarClock },
];


const NAV_BOTTOM: { key: NavKey; label: string; icon: IconType }[] = [
  { key: "personalization", label: "Персонализация", icon: SlidersHorizontal },
  { key: "settings", label: "Настройки", icon: Settings },
];


const SEGMENTS = ["Отдел", "Менеджер", "Объект"];

const PERIODS = ["2 янв - 4 фев", "Неделя", "Месяц", "Год", "За все время"];

type SeriesKey = "high" | "mid" | "low";

const SERIES: {
  key: SeriesKey;
  label: string;
  color: string;
  points: [number, number][];
}[] = [
  {
    key: "high",
    label: "Высокий",
    color: "#1ac779",
    points: [
      [0, 120],
      [160, 90],
      [320, 140],
      [480, 70],
      [640, 110],
      [800, 60],
      [960, 100],
      [1120, 40],
    ],
  },
  {
    key: "mid",
    label: "Средний",
    color: "#f1b91a",
    points: [
      [0, 200],
      [160, 180],
      [320, 150],
      [480, 160],
      [640, 120],
      [800, 130],
      [960, 90],
      [1120, 60],
    ],
  },
  {
    key: "low",
    label: "Низкий",
    color: "#fb414a",
    points: [
      [0, 230],
      [160, 210],
      [320, 220],
      [480, 190],
      [640, 200],
      [800, 170],
      [960, 180],
      [1120, 150],
    ],
  },
];

type Potential = {
  label: string;
  sum: string;
  pct: string;
  color: string;
  lines: [string, string, string][];
};

const POTENTIAL: Potential[] = [
  {
    label: "Высокий потенциал",
    sum: "12,3 млн ₽",
    pct: "65%",
    color: "#1ac779",
    lines: [
      ["Новые", "1200", "226,33 млн ₽"],
      ["На дозвоне", "7", "0 ₽"],
    ],
  },
  {
    label: "Средний потенциал",
    sum: "4,1 млн ₽",
    pct: "20%",
    color: "#f1b91a",
    lines: [
      ["Новые", "1200", "226,33 млн ₽"],
      ["На дозвоне", "7", "0 ₽"],
    ],
  },
  {
    label: "Низкий потенциал",
    sum: "2,8 млн ₽",
    pct: "15%",
    color: "#fb414a",
    lines: [
      ["Новые", "1200", "226,33 млн ₽"],
      ["На дозвоне", "7", "0 ₽"],
    ],
  },
];

type TeamRow = {
  name: string;
  total: string;
  success: string;
  fail: string;
  critical: string;
  efficiency: string;
};

const TEAM_ROWS: TeamRow[] = [
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Алексеева Анастасия",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Макаров Иван",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
  {
    name: "Петрова Ольга",
    total: "385",
    success: "280",
    fail: "20",
    critical: "23",
    efficiency: "72",
  },
];

type Insight = { title: string; items: [string, string][] };

const INSIGHTS: Insight[] = [
  {
    title: "Возражения клиентов",
    items: [
      ["Дорого", "61%"],
      ["Не уверен в районе", "21%"],
      ["Ипотека", "17%"],
      ["Нет подходящих планировок", "10%"],
      ["Другое", "6%"],
    ],
  },
  {
    title: "Причины отказов",
    items: [
      ["Не подобран вариант", "61%"],
      ["Не устроили условия ипотеки", "21%"],
      ["Цена выше ожиданий", "17%"],
      ["Передумал/Отложил", "10%"],
      ["Другое", "6%"],
    ],
  },
  {
    title: "Объекты",
    items: [
      ["ЖК «Алиса»", "61%"],
      ["Дом «Милый дом»", "21%"],
      ["Квартал-парк «Каменные палатки»", "17%"],
      ["ЖК «Южные кварталы»", "10%"],
      ["ЖК «Теплые кварталы»", "6%"],
    ],
  },
  {
    title: "Стадия зрелости",
    items: [
      ["Стадия 5", "61%"],
      ["Стадия 4", "21%"],
      ["Стадия 3", "17%"],
      ["Стадия 2", "10%"],
      ["Стадия 1", "6%"],
    ],
  },
  {
    title: "Цель покупки",
    items: [
      ["Для семьи", "61%"],
      ["Инвестиции", "21%"],
      ["Увеличение площади", "17%"],
      ["Переезд в новостройку", "10%"],
      ["На будущее детям", "6%"],
    ],
  },
];

function BestsellerAI() {
  const [activeNav, setActiveNav] = useState<NavKey>("dashboard");
  const [activeSegment, setActiveSegment] = useState(SEGMENTS[0]);
  const [activePeriod, setActivePeriod] = useState(PERIODS[0]);
  const [visible, setVisible] = useState<Record<SeriesKey, boolean>>({
    high: true,
    mid: true,
    low: true,
  });
  const [collapsed, setCollapsed] = useState(false);
  const [selectedTeam] = useState<number>(-1);

  const toggleSeries = (key: SeriesKey) =>
    setVisible((v) => ({ ...v, [key]: !v[key] }));

  return (
    <div className="ba-page">
      <div className={`ba-layout ${collapsed ? "is-collapsed" : ""}`}>
        {/* ---------- Sidebar ---------- */}
        <aside className="ba-sidebar">
          <div className="ba-brand">
            <div className="ba-brand__logo">BZ</div>
            <div className="ba-brand__meta">
              <span className="ba-brand__name">BAZA Development</span>
              <span className="ba-brand__account">Account-name</span>
            </div>
          </div>

          <nav className="ba-nav">
            {NAV_MAIN.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                className={`ba-nav__item ${activeNav === key ? "is-active" : ""}`}
                onClick={() => setActiveNav(key)}
              >
                <Icon size={20} />
                <span>{label}</span>
              </button>
            ))}

            {NAV_BOTTOM.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                className={`ba-nav__item ${activeNav === key ? "is-active" : ""}`}
                onClick={() => setActiveNav(key)}
              >
                <Icon size={20} />
                <span>{label}</span>
                <ChevronDown size={16} className="ba-nav__chevron" />
              </button>
            ))}
          </nav>

          <button
            type="button"
            className="ba-nav__item ba-nav__collapse"
            onClick={() => setCollapsed((c) => !c)}
          >
            <ChevronsLeft size={20} />
            <span>Свернуть</span>
          </button>
        </aside>

        {/* ---------- Main ---------- */}
        <main className="ba-main">
          {/* Header */}
          <header className="ba-header">
            <h1 className="ba-header__title">Дашборд</h1>
            <div className="ba-filters">
              <div className="ba-filter-group">
                <div className="ba-filter-group__icon">
                  <Filter size={20} />
                </div>
                <div className="ba-segments">
                  {SEGMENTS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className={`ba-segment ${activeSegment === s ? "is-active" : ""}`}
                      onClick={() => setActiveSegment(s)}
                    >
                      <span>{s}</span>
                      <ChevronDown size={16} />
                    </button>
                  ))}
                </div>
              </div>

              <div className="ba-filter-group ba-filter-group--period">
                <div className="ba-filter-group__icon">
                  <Calendar size={20} />
                </div>
                <div className="ba-periods">
                  {PERIODS.map((p) => (
                    <button
                      key={p}
                      type="button"
                      className={`ba-period ${activePeriod === p ? "is-active" : ""}`}
                      onClick={() => setActivePeriod(p)}
                    >
                      <span>{p}</span>
                    </button>
                  ))}
                </div>
              </div>

              <button type="button" className="ba-menu-btn" aria-label="Меню">
                <Search size={20} />
              </button>
              <button type="button" className="ba-menu-btn" aria-label="Ещё">
                <MoreVertical size={20} />
              </button>
            </div>
          </header>

          {/* Content */}
          <div className="ba-content">
            <div className="ba-col-main">
              {/* Top row: two cards */}
              <div className="ba-top-row">
                <section className="ba-card">
                  <div className="ba-card__head">
                    <div className="ba-card__icon ba-card__icon--blue">
                      <TrendingUp size={18} />
                    </div>
                    <h2 className="ba-card__title">Потенциал базы</h2>
                    <div className="ba-card__icon ba-card__icon--ghost">
                      <ExternalLink size={16} />
                    </div>
                  </div>
                  <div className="ba-card__body ba-card__body--split">
                    <div className="ba-potential-list">
                      {POTENTIAL.map((p) => (
                        <article className="ba-potential" key={p.label}>
                          <div className="ba-potential__top">
                            <div className="ba-potential__titles">
                              <span
                                className="ba-potential__label"
                                style={{ color: p.color }}
                              >
                                {p.label}
                              </span>
                              <span className="ba-potential__sum">{p.sum}</span>
                            </div>
                            <span
                              className="ba-potential__pct"
                              style={{ color: p.color }}
                            >
                              {p.pct}
                            </span>
                          </div>
                          <div className="ba-potential__lines">
                            {p.lines.map((line, i) => (
                              <div className="ba-potential__line" key={i}>
                                <span>{line[0]}</span>
                                <span>{line[1]}</span>
                                <span>{line[2]}</span>
                              </div>
                            ))}
                          </div>
                          <button type="button" className="ba-potential__more">
                            Развернуть
                          </button>
                        </article>
                      ))}
                    </div>

                    <div className="ba-donut">
                      <svg viewBox="0 0 200 200" className="ba-donut__svg">
                        <circle
                          cx="100"
                          cy="100"
                          r="80"
                          fill="none"
                          stroke="#f4f4f8"
                          strokeWidth="24"
                        />
                        <circle
                          cx="100"
                          cy="100"
                          r="80"
                          fill="none"
                          stroke="#1ac779"
                          strokeWidth="24"
                          strokeDasharray="408 504"
                          strokeDashoffset="0"
                          transform="rotate(-90 100 100)"
                        />
                        <circle
                          cx="100"
                          cy="100"
                          r="80"
                          fill="none"
                          stroke="#f1b91a"
                          strokeWidth="24"
                          strokeDasharray="126 504"
                          strokeDashoffset="-408"
                          transform="rotate(-90 100 100)"
                        />
                        <circle
                          cx="100"
                          cy="100"
                          r="80"
                          fill="none"
                          stroke="#fb414a"
                          strokeWidth="24"
                          strokeDasharray="94 504"
                          strokeDashoffset="-534"
                          transform="rotate(-90 100 100)"
                        />
                      </svg>
                      <div className="ba-donut__center">
                        <span className="ba-donut__sum">18,7 млн ₽</span>
                        <span className="ba-donut__caption">
                          прогноз выручки
                        </span>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="ba-card">
                  <div className="ba-card__head">
                    <div className="ba-card__icon ba-card__icon--purple">
                      <BarChart2 size={18} />
                    </div>
                    <h2 className="ba-card__title">Эффективность команды</h2>
                  </div>
                  <div className="ba-card__body ba-team">
                    <table className="ba-team__table">
                      <thead>
                        <tr>
                          <th>Менеджер</th>
                          <th>Успешные</th>
                          <th>Неуспешные</th>
                          <th>Критичные</th>
                          <th>Эффективность менеджера</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {TEAM_ROWS.map((row, i) => (
                          <tr
                            key={i}
                            className={selectedTeam === i ? "is-selected" : ""}
                          >
                            <td className="ba-team__name">
                              <span className="ba-team__name-val">
                                {row.name}
                              </span>
                            </td>
                            <td className="ba-team__ok">
                              <span className="ba-team__metric-val">
                                {row.success}
                              </span>
                            </td>
                            <td className="ba-team__warn">
                              <span className="ba-team__metric-val">
                                {row.fail}
                              </span>
                            </td>
                            <td className="ba-team__bad">
                              <span className="ba-team__metric-val">
                                {row.critical}
                              </span>
                            </td>
                            <td className="ba-team__ok">
                              {/* Если здесь нужны и цифра, и иконка рядом, оберните их в div с флексом */}
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "8px",
                                }}
                              >
                                <span className="ba-team__metric-val">
                                  {row.efficiency}
                                </span>
                              </div>
                            </td>
                            <td>
                              <ExternalLink size={20} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>

              {/* Chart card */}
              <section className="ba-chart-card">
                <div className="ba-chart-card__head">
                  <div className="ba-chart-card__title-group">
                    <h2 className="ba-chart-card__title">На графике</h2>
                    <div className="ba-chart-card__select">
                      <span>Потенциал базы</span>
                      <ChevronDown size={16} />
                    </div>
                  </div>
                  <div className="ba-chart-card__tools">
                    <button
                      type="button"
                      className="ba-tool-btn"
                      aria-label="График"
                    >
                      <LineChart size={18} />
                    </button>
                    <button
                      type="button"
                      className="ba-tool-btn"
                      aria-label="График2"
                    >
                      <BarChart2 size={18} />
                    </button>
                  </div>
                </div>

                <div className="ba-chart-card__body">
                  <div className="ba-chart">
                    <svg
                      viewBox="0 0 1120 240"
                      preserveAspectRatio="none"
                      role="img"
                      aria-label="График по периоду"
                    >
                      {SERIES.filter((s) => visible[s.key]).map((s) => (
                        <polyline
                          key={s.key}
                          points={s.points.map((p) => p.join(",")).join(" ")}
                          fill="none"
                          stroke={s.color}
                          strokeWidth={1}
                        />
                      ))}
                      <line
                        x1="28"
                        y1="0"
                        x2="28"
                        y2="240"
                        stroke="#d8e6f4"
                        strokeWidth="0.5"
                      />
                    </svg>
                    <div className="ba-chart__tooltip">28.02</div>
                    <div className="ba-chart__popover">
                      <div className="ba-chart__popover-date">
                        Пятница, 28 февраля 2026
                      </div>
                      <div className="ba-chart__popover-body">
                        <div className="ba-chart__popover-row">
                          <span className="ba-dot ba-dot--green" />
                          <span>Высокий потенциал</span>
                          <span className="ba-chart__popover-val">28</span>
                        </div>
                        <div className="ba-chart__popover-row">
                          <span className="ba-dot ba-dot--yellow" />
                          <span>Средний потенциал</span>
                          <span className="ba-chart__popover-val">10</span>
                        </div>
                        <div className="ba-chart__popover-row">
                          <span className="ba-dot ba-dot--red" />
                          <span>Низкий потенциал</span>
                          <span className="ba-chart__popover-val">13</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="ba-chart__footer">
                    <div className="ba-legend">
                      {SERIES.map((s) => (
                        <button
                          key={s.key}
                          type="button"
                          className={`ba-legend__item ${visible[s.key] ? "" : "is-off"}`}
                          onClick={() => toggleSeries(s.key)}
                        >
                          <span
                            className="ba-legend__check"
                            style={{ borderColor: s.color }}
                          >
                            {visible[s.key] && (
                              <Check size={12} color={s.color} />
                            )}
                          </span>
                          <span className="ba-legend__label">{s.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {/* Right insights panel */}
            <aside className="ba-insights-panel">
              <div className="ba-insights-panel__head">
                <div className="ba-insights-panel__icon">
                  <Lightbulb size={18} />
                </div>
                <h2 className="ba-insights-panel__title">Инсайты</h2>
              </div>

              <div className="ba-insights">
                {INSIGHTS.map((insight) => (
                  <article className="ba-insight" key={insight.title}>
                    <div className="ba-insight__top">
                      <h3 className="ba-insight__title">{insight.title}</h3>
                    </div>
                    <div className="ba-insight__bars">
                      {insight.items.map(([label, pct], i) => (
                        <div className="ba-insight__indicator" key={i}>
                          <span className="ba-insight__label">{label}</span>
                          <span className="ba-insight__track">
                            <span
                              className="ba-insight__fill"
                              style={{ width: pct }}
                            />
                          </span>
                          <span className="ba-insight__pct">{pct}</span>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}

export default BestsellerAI;
