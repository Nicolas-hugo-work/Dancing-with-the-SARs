import { CalendarDays, History, Play } from "lucide-react";

type TimelineBarProps = {
  years: readonly number[];
  activeYear: number;
};

export default function TimelineBar({ years, activeYear }: TimelineBarProps) {
  const activeIndex = Math.max(0, years.indexOf(activeYear));
  const progress =
    years.length > 1 ? (activeIndex / years.length) * 100 : 100;

  return (
    <section
      aria-label="Línea de tiempo histórica"
      className="panel-texture panel-texture-grain fixed bottom-4 left-4 right-4 z-50 flex h-16 items-center justify-between gap-4 rounded-2xl border border-[#184C32]/15 bg-[#F3E7E1]/90 px-6 shadow-2xl shadow-[#184C32]/20 backdrop-blur-md"
    >
      <div className="relative z-10 hidden shrink-0 items-center gap-3 sm:flex">
        <span className="grid h-9 w-9 place-items-center rounded-xl border border-[#184C32] bg-[#184C32] text-[#F2E4DD]">
          <History
            className="h-4 w-4"
            strokeWidth={1.9}
            aria-hidden="true"
          />
        </span>
        <div className="leading-tight">
          <p className="text-[8px] font-extrabold uppercase tracking-[0.2em] text-[#184C32]/60">
            Evolución
          </p>
          <p className="font-display text-[13px] text-[#184C32]">
            Línea de tiempo
          </p>
        </div>
      </div>

      <div className="relative z-10 min-w-0 flex-1 px-0 sm:px-6">
        <div
          aria-hidden="true"
          className="absolute left-0 right-0 top-[7px] h-px bg-[#184C32]/15 sm:left-6 sm:right-6"
        />
        <div
          aria-hidden="true"
          className="absolute left-0 top-[7px] h-px bg-[#184C32]/50 sm:left-6"
          style={{ width: `calc(${progress}% - ${progress > 0 ? 6.5 : 0}px)` }}
        />

        <ol className="relative flex items-start justify-between">
          {years.map((year) => {
            const isActive = year === activeYear;

            return (
              <li
                key={year}
                className="relative z-10 flex flex-col items-center gap-1.5"
              >
                <span
                  className={`grid h-3.5 w-3.5 place-items-center rounded-full border-2 ${
                    isActive
                      ? "border-[#184C32] bg-[#F2E4DD] ring-2 ring-[#184C32]/10"
                      : "border-[#184C32]/40 bg-[#184C32]"
                  }`}
                >
                  {isActive && (
                    <span className="h-1.5 w-1.5 rounded-full bg-[#184C32]" />
                  )}
                </span>
                <span
                  className={`text-[10px] font-extrabold tabular-nums ${
                    isActive ? "text-[#184C32]" : "text-[#184C32]/60"
                  }`}
                >
                  {year}
                </span>
              </li>
            );
          })}

          <li className="relative z-10 flex flex-col items-center gap-1.5">
            <span className="h-3.5 w-3.5 rounded-full border border-dashed border-[#184C32]/60 bg-[#F2E4DD]" />
            <span className="text-[10px] font-extrabold text-[#184C32]/60">
              +2 años
            </span>
          </li>
        </ol>
      </div>

      <div className="relative z-10 flex shrink-0 items-center gap-2 sm:gap-3">
        <span className="hidden items-center gap-2 rounded-lg border border-[#184C32]/20 px-3 py-2 lg:flex">
          <CalendarDays
            className="h-3.5 w-3.5 text-[#184C32]"
            strokeWidth={2}
            aria-hidden="true"
          />
          <span className="text-[9px] font-extrabold uppercase tracking-[0.14em] text-[#184C32]">
            Actual{" "}
            <span className="tabular-nums">{activeYear}</span>
          </span>
        </span>

        <button
          type="button"
          aria-label="Reproducir línea de tiempo"
          title="Reproducir"
          className="group grid h-9 w-9 place-items-center rounded-lg border border-[#184C32]/15 bg-[#4DB8D6] text-[#0F3021] shadow-lg shadow-[#184C32]/20 transition-all duration-300 hover:-translate-y-0.5 hover:bg-[#35A5C4] hover:shadow-xl active:translate-y-0 active:bg-[#2F96B3] active:shadow-md"
        >
          <Play
            className="h-3.5 w-3.5 fill-current transition-all duration-300 group-hover:scale-110"
            strokeWidth={1.5}
            aria-hidden="true"
          />
        </button>
      </div>
    </section>
  );
}
