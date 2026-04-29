import "@/styles/globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "crypto-trading-bot",
  description: "Local Binance trading bot dashboard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg text-[#d9d7ce] min-h-screen">
        <div className="max-w-7xl mx-auto p-6">{children}</div>
      </body>
    </html>
  );
}
