import { ServiceStatusGrid } from "@/components/dashboard/ServiceStatusGrid";
import { ConnectionBadge } from "@/components/dashboard/ConnectionBadge";

export default function DashboardPage() {
  return (
    <main>
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-accent">crypto-trading-bot</h1>
          <p className="text-sm opacity-70">Phase 0 — scaffold &amp; testnet read-only</p>
        </div>
        <ConnectionBadge />
      </header>

      <section className="space-y-6">
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
