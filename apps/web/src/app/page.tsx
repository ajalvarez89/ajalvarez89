import { ServiceStatusGrid } from "@/components/dashboard/ServiceStatusGrid";
import { ConnectionBadge } from "@/components/dashboard/ConnectionBadge";
import { MarketView } from "@/components/dashboard/MarketView";
import { PnlSummary } from "@/components/dashboard/PnlSummary";
import { OpenPositions } from "@/components/dashboard/OpenPositions";
import { RecentOrders } from "@/components/dashboard/RecentOrders";
import { AdminBar } from "@/components/dashboard/AdminBar";

export default function DashboardPage() {
  return (
    <main>
      <header className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-accent">crypto-trading-bot</h1>
          <p className="text-sm opacity-70">Phase 2 — paper trading + dashboard P&amp;L</p>
        </div>
        <ConnectionBadge />
      </header>

      <section className="space-y-6">
        <div className="bg-panel border border-border rounded-lg p-4">
          <AdminBar />
        </div>

        <div className="bg-panel border border-border rounded-lg p-5">
          <h2 className="text-lg font-semibold mb-4">P&amp;L</h2>
          <PnlSummary />
        </div>

        <div className="bg-panel border border-border rounded-lg p-5">
          <h2 className="text-lg font-semibold mb-4">Live market</h2>
          <MarketView />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-panel border border-border rounded-lg p-5">
            <h2 className="text-lg font-semibold mb-4">Open positions</h2>
            <OpenPositions />
          </div>
          <div className="bg-panel border border-border rounded-lg p-5">
            <h2 className="text-lg font-semibold mb-4">Recent orders</h2>
            <RecentOrders />
          </div>
        </div>

        <div className="bg-panel border border-border rounded-lg p-5">
          <h2 className="text-lg font-semibold mb-4">Service status</h2>
          <ServiceStatusGrid />
        </div>

        <div className="bg-panel border border-border rounded-lg p-5">
          <h2 className="text-lg font-semibold mb-2">⚠️ Disclaimer</h2>
          <p className="text-sm opacity-80">
            Software experimental. El trading de criptomonedas conlleva riesgo de pérdida total. Sin garantía de rentabilidad.
            Empieza siempre en testnet o paper trading.
          </p>
        </div>
      </section>
    </main>
  );
}
