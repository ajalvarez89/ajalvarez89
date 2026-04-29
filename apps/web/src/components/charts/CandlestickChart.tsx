"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts";
import type { Kline } from "@/lib/hooks/useMarketKlines";

interface Props {
  klines: Kline[];
  height?: number;
}

export function CandlestickChart({ klines, height = 420 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: "#11151c" },
        textColor: "#d9d7ce",
      },
      grid: {
        vertLines: { color: "#1f2430" },
        horzLines: { color: "#1f2430" },
      },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#1f2430" },
      rightPriceScale: { borderColor: "#1f2430" },
      width: containerRef.current.clientWidth,
      height,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#4ade80",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#4ade80",
      wickDownColor: "#f87171",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  // Keep series in sync with klines.
  useEffect(() => {
    if (!seriesRef.current || klines.length === 0) return;

    const data: CandlestickData<Time>[] = klines.map((k) => ({
      time: Math.floor(k.open_time_ms / 1000) as Time,
      open: k.open,
      high: k.high,
      low: k.low,
      close: k.close,
    }));
    // setData replaces the entire dataset; for streaming updates the parent
    // updates the last entry in `klines`, so reusing setData each render is
    // simple and fast at this dataset size.
    seriesRef.current.setData(data);
  }, [klines]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
